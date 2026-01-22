#!/usr/bin/env python3
"""
Check plugin for Veeam Backup Objects as services on the Veeam server.

This check creates individual services for each backup object (VM, agent backup)
directly on the Veeam server. Alternative to piggyback mode.
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

Section = dict[str, dict[str, Any]]  # name -> object data


def parse_veeam_rest_backup_objects(string_table: StringTable) -> Section | None:
    """Parse JSON list of backup objects into dict by name."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        objects = json.loads(json_str)

        # Convert list to dict keyed by object name
        result: Section = {}
        for obj in objects:
            name = obj.get("name")
            if name:
                result[name] = obj
        return result if result else None
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_backup_objects = AgentSection(
    name="veeam_rest_backup_objects",
    parse_function=parse_veeam_rest_backup_objects,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_backup_objects(section: Section) -> DiscoveryResult:
    """Discover one service per backup object."""
    for name in section:
        yield Service(item=name)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

# Backup object type display names
TYPE_DISPLAY = {
    "VirtualMachine": "VM",
    "Computer": "Agent",
    "VCloud": "vCloud",
}


def check_veeam_rest_backup_objects(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check backup status for a specific backup object."""
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="Backup object not found")
        return

    obj = section[item]

    # Determine status from lastRunFailed
    last_run_failed = obj.get("lastRunFailed", False)
    restore_point_count = obj.get("restorePointsCount", 0)

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
    obj_type = obj.get("type", "Unknown")
    type_display = TYPE_DISPLAY.get(obj_type, obj_type)
    platform = obj.get("platformName", "")
    job_name = obj.get("jobName")

    summary = f"{result_text}"
    if job_name:
        summary += f", Job: {job_name}"
    summary += f", Type: {type_display}"
    if platform:
        summary += f" ({platform})"
    summary += f", Restore points: {restore_point_count}"

    yield Result(state=result_state, summary=summary)

    # Check for warning/error info from task sessions (e.g., VSS errors)
    warning_info = obj.get("warningInfo")
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

    # Restore points count with optional min/max thresholds
    yield Metric("veeam_rest_backup_restore_points", restore_point_count)

    # Check minimum restore points
    min_warn = params.get("restore_points_min_warn")
    min_crit = params.get("restore_points_min_crit")
    if min_warn is not None or min_crit is not None:
        yield from check_levels(
            restore_point_count,
            levels_lower=(min_warn, min_crit) if min_warn is not None and min_crit is not None else None,
            render_func=lambda x: str(int(x)),
            label="Restore points",
            notice_only=True,
        )

    # Check maximum restore points
    max_warn = params.get("restore_points_max_warn")
    max_crit = params.get("restore_points_max_crit")
    if max_warn is not None or max_crit is not None:
        yield from check_levels(
            restore_point_count,
            levels_upper=(max_warn, max_crit) if max_warn is not None and max_crit is not None else None,
            render_func=lambda x: str(int(x)),
            label="Restore points",
            notice_only=True,
        )

    # Backup age from enrichment
    backup_age = obj.get("backupAgeSeconds")
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
    task_data = obj.get("taskData")
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

        # Avg speed if available
        avg_speed = progress.get("avgSpeed")
        if avg_speed is not None:
            yield Metric("veeam_rest_backup_avg_speed", avg_speed)

        # Total size from progress if available
        total_size = progress.get("totalSize")
        if total_size is not None:
            yield Metric("veeam_rest_backup_total_size", total_size)

    # Latest restore point details (fallback for size if no task data)
    latest_rp = obj.get("latestRestorePoint")
    if latest_rp:
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

        # Additional restore point metrics
        backup_size = latest_rp.get("backupSize")
        if backup_size is not None:
            yield Metric("veeam_rest_backup_backup_size", backup_size)

        # Data size from restore point
        data_size = latest_rp.get("dataSize")
        if data_size is not None:
            yield Metric("veeam_rest_backup_data_size", data_size)

    # Backup server info
    backup_server = obj.get("backupServer")
    if backup_server:
        yield Result(state=State.OK, notice=f"Backup server: {backup_server}")


check_plugin_veeam_rest_backup_objects = CheckPlugin(
    name="veeam_rest_backup_objects",
    service_name="Veeam Backup %s",
    discovery_function=discover_veeam_rest_backup_objects,
    check_function=check_veeam_rest_backup_objects,
    check_default_parameters={},
    check_ruleset_name="veeam_rest_backup",
)
