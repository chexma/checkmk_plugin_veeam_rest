#!/usr/bin/env python3
"""
Check plugin for Veeam Backup Jobs.

Monitors backup and replication job status, last result, and schedule.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    render,
)

from cmk_addons.plugins.veeam_rest.lib import (
    parse_duration_to_seconds,
    parse_json_section,
    parse_rate_to_bytes_per_second,
)


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = dict[str, dict[str, Any]]  # "Category - Name" -> job data


def _get_job_item(job: dict[str, Any]) -> str | None:
    """Get the service item name for a job."""
    name = job.get("name")
    if not name:
        return None
    category = _get_job_category(job)
    return f"{category} - {name}"


def parse_veeam_rest_jobs(string_table) -> Section | None:
    """Parse JSON list of jobs into dict by 'Category - Name' for O(1) lookup."""
    data = parse_json_section(string_table)
    if not data or not isinstance(data, list):
        return None
    result = {}
    for job in data:
        item = _get_job_item(job)
        if item:
            result[item] = job
    return result or None


agent_section_veeam_rest_jobs = AgentSection(
    name="veeam_rest_jobs",
    parse_function=parse_veeam_rest_jobs,
)


# =============================================================================
# JOB TYPE MAPPING
# =============================================================================

# Map API job types to human-readable category prefixes
JOB_TYPE_CATEGORY = {
    # VMware
    "VSphereBackup": "VMware Backup",
    "VSphereReplica": "VMware Replica",
    # Hyper-V
    "HyperVBackup": "Hyper-V Backup",
    "HyperVReplica": "Hyper-V Replica",
    # Cloud Director
    "CloudDirectorBackup": "vCD Backup",
    # Entra ID (Azure AD)
    "EntraIDTenantBackup": "Entra ID Backup",
    "EntraIDAuditLogBackup": "Entra ID Audit",
    "EntraIDTenantBackupCopy": "Entra ID Copy",
    # Backup Copy
    "BackupCopy": "Backup Copy",
    "FileBackupCopy": "File Backup Copy",
    "LegacyBackupCopy": "Legacy Copy",
    # Agent Backup
    "WindowsAgentBackup": "Windows Agent",
    "LinuxAgentBackup": "Linux Agent",
    "WindowsAgentBackupWorkstationPolicy": "Win Workstation",
    "LinuxAgentBackupWorkstationPolicy": "Linux Workstation",
    "WindowsAgentBackupServerPolicy": "Win Server Policy",
    "LinuxAgentBackupServerPolicy": "Linux Server Policy",
    # File and Object
    "FileBackup": "File Backup",
    "ObjectStorageBackup": "Object Storage",
    # Cloud
    "CloudBackupAzure": "Azure Backup",
    "CloudBackupAWS": "AWS Backup",
    "CloudBackupGoogle": "GCP Backup",
    # Other
    "SureBackupContentScan": "SureBackup Scan",
    "Unknown": "Backup",
}


def _get_job_category(job: dict[str, Any]) -> str:
    """Determine the job category for service naming."""
    job_type = job.get("type", "Unknown")
    return JOB_TYPE_CATEGORY.get(job_type, job_type)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_jobs(section: Section) -> DiscoveryResult:
    """Discover backup jobs."""
    if not section:
        return

    for item in section:
        yield Service(item=item)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

# Default mapping of Veeam result to Checkmk state
DEFAULT_RESULT_STATE_MAP = {
    "Success": "ok",
    "Warning": "warn",
    "Failed": "crit",
    "None": "ok",  # No run yet
}

# Default mapping of Veeam job status to Checkmk state
DEFAULT_STATUS_STATE_MAP = {
    "Running": "ok",
    "Inactive": "ok",
    "Disabled": "warn",
    "Enabled": "ok",
    "Stopping": "ok",
    "Stopped": "ok",
    "Starting": "ok",
}

# Mapping of Veeam job status to display text
JOB_STATUS_MAP = {
    "Running": "running",
    "Inactive": "inactive",
    "Disabled": "disabled",
    "Enabled": "enabled",
    "Stopping": "stopping",
    "Stopped": "stopped",
    "Starting": "starting",
}

# Convert string state to State enum
STATE_MAP = {
    "ok": State.OK,
    "warn": State.WARN,
    "crit": State.CRIT,
}


def _format_datetime(iso_string: str | None) -> str | None:
    """Format ISO 8601 datetime to readable format (DD.MM.YYYY HH:MM:SS)."""
    if not iso_string:
        return None
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except (ValueError, TypeError):
        return iso_string  # Return original if parsing fails


def _get_result_state(result: str, params: Mapping[str, Any]) -> State:
    """Get the configured state for a job result."""
    result_states = params.get("result_states", {})
    # Map "None" from Veeam API to "no_result" key in params (None is reserved in Python)
    param_key = "no_result" if result == "None" else result
    state_str = result_states.get(param_key, DEFAULT_RESULT_STATE_MAP.get(result, "ok"))
    return STATE_MAP.get(state_str, State.OK)


def _get_status_state(status: str, params: Mapping[str, Any]) -> State:
    """Get the configured state for a job status."""
    status_states = params.get("status_states", {})
    state_str = status_states.get(status, DEFAULT_STATUS_STATE_MAP.get(status, "ok"))
    return STATE_MAP.get(state_str, State.OK)


def check_veeam_rest_jobs(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check a single backup job."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # O(1) lookup by "Category - Name"
    job = section.get(item)
    if job is None:
        yield Result(state=State.UNKNOWN, summary="Job not found")
        return

    # Extract job properties
    job_type = job.get("type", "Unknown")
    status = job.get("status", "Unknown")
    last_result = job.get("lastResult", "None")
    last_run = job.get("lastRun")
    next_run = job.get("nextRun")
    progress = job.get("progressPercent", 0)
    objects_count = job.get("objectsCount", 0)
    repository = job.get("repositoryName", "")
    last_run_age = job.get("lastRunAgeSeconds")

    # Determine state based on last result (configurable)
    result_state = _get_result_state(last_result, params)

    # Determine state based on job status (configurable)
    status_state = _get_status_state(status, params)

    # Use the worst state between result and status
    state = State.worst(result_state, status_state)

    # Check if job is disabled and ignore_disabled is set
    if status == "Disabled" and params.get("ignore_disabled", False):
        yield Result(state=State.OK, summary="Job is disabled (ignored)")
        return

    # Build summary
    status_text = JOB_STATUS_MAP.get(status, status)
    summary_parts = [f"Status: {status_text}", f"Last result: {last_result}"]

    # Check if job is running
    if status == "Running":
        summary_parts.append(f"Progress: {progress}%")
    else:
        # Add duration and processed size for completed jobs
        session_progress = job.get("sessionProgress", {}) or {}
        duration = session_progress.get("duration", "")
        processed_size = session_progress.get("processedSize", 0)

        if duration:
            summary_parts.append(f"Last Duration: {duration}")
        if processed_size and processed_size > 0:
            summary_parts.append(f"Processed: {render.bytes(processed_size)}")

    yield Result(state=state, summary=", ".join(summary_parts))

    # Check max job age
    max_age = params.get("max_job_age")
    if max_age is not None and last_run_age is not None:
        max_age_seconds = max_age * 3600  # Convert hours to seconds
        if last_run_age > max_age_seconds:
            age_text = render.timespan(last_run_age)
            yield Result(
                state=State.WARN,
                summary=f"Last run {age_text} ago exceeds threshold of {max_age}h",
            )

    # Additional properties for details
    description = job.get("description", "")
    workload = job.get("workload", "")
    high_priority = job.get("highPriority", False)
    is_storage_snapshot = job.get("isStorageSnapshot", False)
    backup_server = job.get("backupServer", "")
    next_run_policy = job.get("nextRunPolicy", "")
    session_progress = job.get("sessionProgress", {})

    # Session progress details
    duration = session_progress.get("duration", "")
    bottleneck = session_progress.get("bottleneck", "")
    processed_size = session_progress.get("processedSize", 0)
    read_size = session_progress.get("readSize", 0)
    transferred_size = session_progress.get("transferredSize", 0)
    processing_rate = session_progress.get("processingRate", "")

    # Details section
    yield Result(state=State.OK, notice=f"Type: {job_type}")
    yield Result(state=State.OK, notice=f"Objects: {objects_count}")

    if repository:
        yield Result(state=State.OK, notice=f"Repository: {repository}")

    if description:
        yield Result(state=State.OK, notice=f"Description: {description}")

    if workload:
        yield Result(state=State.OK, notice=f"Workload: {workload}")

    if backup_server:
        yield Result(state=State.OK, notice=f"Backup Server: {backup_server}")

    if last_run:
        last_run_formatted = _format_datetime(last_run) or last_run
        yield Result(state=State.OK, notice=f"Last Run: {last_run_formatted}")

    if next_run:
        next_run_formatted = _format_datetime(next_run) or next_run
        yield Result(state=State.OK, notice=f"Next Run: {next_run_formatted}")

    if next_run_policy and next_run_policy != "<Not scheduled>":
        yield Result(state=State.OK, notice=f"Schedule Policy: {next_run_policy}")

    # Session progress details
    if duration:
        yield Result(state=State.OK, notice=f"Last Duration: {duration}")

    if processed_size > 0:
        yield Result(state=State.OK, notice=f"Processed: {render.disksize(processed_size)}")

    if read_size > 0:
        yield Result(state=State.OK, notice=f"Read: {render.disksize(read_size)}")

    if transferred_size > 0:
        yield Result(state=State.OK, notice=f"Transferred: {render.disksize(transferred_size)}")

    if processing_rate:
        yield Result(state=State.OK, notice=f"Speed: {processing_rate}")

    if bottleneck and bottleneck not in ("NotDefined", "Unknown"):
        yield Result(state=State.OK, notice=f"Bottleneck: {bottleneck}")

    # Flags
    flags = []
    if high_priority:
        flags.append("High Priority")
    if is_storage_snapshot:
        flags.append("Storage Snapshot")
    if flags:
        yield Result(state=State.OK, notice=f"Flags: {', '.join(flags)}")

    # Metrics for graphing
    duration_seconds = parse_duration_to_seconds(duration)
    if duration_seconds is not None:
        yield Metric("veeam_rest_job_duration", duration_seconds)

    if processed_size and processed_size > 0:
        yield Metric("veeam_rest_job_size_processed", processed_size)

    if read_size and read_size > 0:
        yield Metric("veeam_rest_job_size_read", read_size)

    if transferred_size and transferred_size > 0:
        yield Metric("veeam_rest_job_size_transferred", transferred_size)

    speed_bytes = parse_rate_to_bytes_per_second(processing_rate)
    if speed_bytes is not None:
        yield Metric("veeam_rest_job_speed", speed_bytes)


check_plugin_veeam_rest_jobs = CheckPlugin(
    name="veeam_rest_jobs",
    service_name="Veeam Job %s",
    discovery_function=discover_veeam_rest_jobs,
    check_function=check_veeam_rest_jobs,
    check_default_parameters={
        "ignore_disabled": False,
        "result_states": {},  # Use defaults from DEFAULT_RESULT_STATE_MAP
        "status_states": {},  # Use defaults from DEFAULT_STATUS_STATE_MAP
    },
    check_ruleset_name="veeam_rest_jobs",
)
