#!/usr/bin/env python3
"""
Check plugin for Veeam VM/Agent Backup status via piggyback.

This check receives backup status data attached to monitored VMs/computers
via Checkmk's piggyback mechanism. Data comes from the backupObjects API,
enriched with task data for VM backups.
"""

import json
from collections.abc import Mapping
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
    StringTable,
    check_levels,
    render,
)

from cmk_addons.plugins.veeam_rest.lib import (
    format_duration_hms,
    parse_rate_to_bytes_per_second,
)


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = dict[str, Any]


def parse_veeam_rest_vm_backup(string_table: StringTable) -> Section | None:
    """Parse JSON output from piggyback data."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_vm_backup = AgentSection(
    name="veeam_rest_vm_backup",
    parse_function=parse_veeam_rest_vm_backup,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_vm_backup(section: Section) -> DiscoveryResult:
    """Discover VM/Agent backup service from piggyback data."""
    if section:
        # Use object name as item for consistent service naming with server-side services
        item = section.get("name", "Unknown")
        yield Service(item=item)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

# Backup object type display names
TYPE_DISPLAY = {
    "VirtualMachine": "VM",
    "Computer": "Agent",
    "VCloud": "vCloud",
}


def check_veeam_rest_vm_backup(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check backup status from backupObjects piggyback data."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No backup data received")
        return

    # Determine status from lastRunFailed
    last_run_failed = section.get("lastRunFailed", False)
    restore_point_count = section.get("restorePointsCount", 0)

    if last_run_failed:
        result_state = State.CRIT
        result_text = "Last backup failed"
    elif restore_point_count == 0:
        result_state = State.WARN
        result_text = "No restore points"
    else:
        result_state = State.OK
        result_text = "OK"

    # Object type for display
    obj_type = section.get("type", "Unknown")
    type_display = TYPE_DISPLAY.get(obj_type, obj_type)
    platform = section.get("platformName", "")
    job_name = section.get("jobName")

    summary = f"{result_text}"
    if job_name:
        summary += f", Job: {job_name}"
    summary += f", Type: {type_display}"
    if platform:
        summary += f" ({platform})"
    summary += f", Restore points: {restore_point_count}"

    yield Result(state=result_state, summary=summary)

    # Restore points count with optional min/max thresholds
    yield Metric("veeam_rest_backup_restore_points", restore_point_count)

    # Check minimum restore points
    min_warn = params.get("restore_points_min_warn")
    min_crit = params.get("restore_points_min_crit")
    if min_warn is not None and min_crit is not None:
        yield from check_levels(
            restore_point_count,
            levels_lower=("fixed", (float(min_warn), float(min_crit))),
            render_func=lambda x: str(int(x)),
            label="Restore points",
            notice_only=True,
        )

    # Check maximum restore points
    max_warn = params.get("restore_points_max_warn")
    max_crit = params.get("restore_points_max_crit")
    if max_warn is not None and max_crit is not None:
        yield from check_levels(
            restore_point_count,
            levels_upper=("fixed", (float(max_warn), float(max_crit))),
            render_func=lambda x: str(int(x)),
            label="Restore points",
            notice_only=True,
        )

    # Check for warning/error info from task sessions (e.g., VSS errors)
    warning_info = section.get("warningInfo")
    if warning_info:
        warning_title = warning_info.get("warningTitle", "Unknown")
        warning_msg = warning_info.get("warningMessage", "")
        warning_job = warning_info.get("jobName", "")
        severity = warning_info.get("severity", "Warning")

        # Failed = CRIT, Warning = WARN
        issue_state = State.CRIT if severity == "Failed" else State.WARN
        issue_label = "Job error" if severity == "Failed" else "Job warning"

        yield Result(
            state=issue_state,
            summary=f"{issue_label}: {warning_title}"
        )
        if warning_msg:
            yield Result(state=State.OK, notice=f"{severity} details: {warning_msg}")
        if warning_job:
            yield Result(state=State.OK, notice=f"{severity} from job: {warning_job}")

    # Backup age from enrichment
    backup_age = section.get("backupAgeSeconds")
    if backup_age is not None:
        age_warn = params.get("backup_age_warn")
        age_crit = params.get("backup_age_crit")

        yield from check_levels(
            backup_age,
            levels_upper=(age_warn, age_crit) if age_warn and age_crit else None,
            metric_name="veeam_rest_backup_age",
            render_func=render.timespan,
            label="Backup age",
        )

    # Task data (available for VM backups only, not agent backups)
    task_data = section.get("taskData")
    if task_data:
        progress = task_data.get("progress") or {}

        # Processed size from task (more accurate than restore point)
        processed_size = progress.get("processedSize")
        if processed_size is not None:
            yield Result(state=State.OK, summary=f"Processed: {render.bytes(processed_size)}")
            yield Metric("veeam_rest_backup_size_processed", processed_size)

        # Duration from task
        duration = task_data.get("durationSeconds")
        if duration is not None:
            yield Result(state=State.OK, summary=f"Duration: {format_duration_hms(duration)}")
            yield Metric("veeam_rest_backup_duration", duration)

        # Speed/processing rate
        rate = progress.get("processingRate")
        if rate:
            speed = parse_rate_to_bytes_per_second(rate)
            if speed is not None:
                yield Result(state=State.OK, notice=f"Speed: {render.iobandwidth(speed)}")
                yield Metric("veeam_rest_backup_speed", speed)

        # Bottleneck
        bottleneck = progress.get("bottleneck")
        if bottleneck and bottleneck not in ("NotDefined", "Unknown"):
            yield Result(state=State.OK, notice=f"Bottleneck: {bottleneck}")

        # Additional size metrics from task
        read_size = progress.get("readSize")
        if read_size is not None:
            yield Metric("veeam_rest_backup_size_read", read_size)

        transferred_size = progress.get("transferredSize")
        if transferred_size is not None:
            yield Metric("veeam_rest_backup_size_transferred", transferred_size)

    # Latest restore point details (fallback for size if no task data)
    latest_rp = section.get("latestRestorePoint")
    if latest_rp:
        # Malware status from backup scan
        malware_status = latest_rp.get("malwareStatus")
        if malware_status:
            # Get configured state mapping (defaults: Clean=OK, Infected=CRIT, Suspicious=WARN, NotScanned=WARN)
            malware_states = params.get("malware_status_states", {})
            default_mapping = {
                "Clean": State.OK,
                "Infected": State.CRIT,
                "Suspicious": State.WARN,
                "NotScanned": State.WARN,
            }
            state_str_map = {"ok": State.OK, "warn": State.WARN, "crit": State.CRIT}
            # Apply user-configured overrides
            for status, state_str in malware_states.items():
                if state_str in state_str_map:
                    default_mapping[status] = state_str_map[state_str]

            status_state = default_mapping.get(malware_status, State.OK)
            yield Result(state=status_state, summary=f"Malware scan: {malware_status}")

        # Size from restore point (only if no task data provided processedSize)
        if not task_data or not (task_data.get("progress") or {}).get("processedSize"):
            original_size = latest_rp.get("originalSize")
            if original_size is not None:
                yield Result(state=State.OK, summary=f"Size: {render.bytes(original_size)}")
                yield Metric("veeam_rest_backup_size_processed", original_size)

        # Creation time as notice
        creation_time = latest_rp.get("creationTime")
        if creation_time:
            yield Result(state=State.OK, notice=f"Last backup: {creation_time}")

    # Backup server info
    backup_server = section.get("backupServer")
    if backup_server:
        yield Result(state=State.OK, notice=f"Backup server: {backup_server}")


check_plugin_veeam_rest_vm_backup = CheckPlugin(
    name="veeam_rest_vm_backup",
    service_name="Veeam Backup %s",
    discovery_function=discover_veeam_rest_vm_backup,
    check_function=check_veeam_rest_vm_backup,
    check_default_parameters={
        "malware_status_states": {},  # Use defaults: Clean=OK, Infected=CRIT, Suspicious=WARN, NotScanned=WARN
    },
    check_ruleset_name="veeam_rest_backup",
)
