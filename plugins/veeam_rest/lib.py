#!/usr/bin/env python3
"""
Shared utility functions for Veeam REST monitoring plugin.
"""

import json
from collections.abc import Iterator, Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckResult,
    Metric,
    Result,
    State,
    StringTable,
    check_levels,
    render,
)


# =============================================================================
# SECTION PARSING
# =============================================================================


def parse_json_section(string_table: StringTable) -> list[dict[str, Any]] | dict[str, Any] | None:
    """Parse JSON output from special agent sections.

    This is the generic JSON parser used by all Veeam REST check plugins.
    Handles both list and dict JSON structures.

    Args:
        string_table: Raw string table from agent output.

    Returns:
        Parsed JSON as list or dict, or None if parsing fails.
    """
    if not string_table:
        return None
    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


# =============================================================================
# RATE & DURATION PARSING
# =============================================================================


def parse_rate_to_bytes_per_second(rate_str: str) -> float | None:
    """Parse rate string like '1,1 GB/s', '500 MB/s', or '131,9 MB' to bytes/second.

    Note: Veeam API may return rate without '/s' suffix (e.g., '131,9 MB').
    """
    if not rate_str:
        return None
    try:
        # Handle European decimal format (1,1 -> 1.1)
        rate_str = rate_str.replace(",", ".")
        parts = rate_str.split()
        if len(parts) != 2:
            return None
        value = float(parts[0])
        unit = parts[1].upper()
        # Support both "MB/S" and "MB" formats (Veeam API inconsistency)
        multipliers = {
            "B/S": 1,
            "KB/S": 1024,
            "MB/S": 1024**2,
            "GB/S": 1024**3,
            "TB/S": 1024**4,
            "B": 1,
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
            "TB": 1024**4,
        }
        return value * multipliers.get(unit, 1)
    except (ValueError, IndexError):
        return None


def parse_duration_to_seconds(duration_str: str) -> int | None:
    """Parse duration string like '00:03:26' or '1.00:03:26' to seconds."""
    if not duration_str:
        return None
    try:
        parts = duration_str.split(":")
        if len(parts) == 3:
            # Check if first part contains days (e.g., "1.00")
            hours_part = parts[0]
            if "." in hours_part:
                days_str, hours_str = hours_part.split(".", 1)
                days = int(days_str)
                hours = int(hours_str)
            else:
                days = 0
                hours = int(hours_part)
            minutes = int(parts[1])
            seconds = int(parts[2])
            return days * 86400 + hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        pass
    return None


def format_duration_hms(seconds: int) -> str:
    """Format duration as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# =============================================================================
# BACKUP CHECK HELPERS
# =============================================================================

# Default malware status to state mapping
MALWARE_STATUS_DEFAULTS: dict[str, str] = {
    "Clean": "ok",
    "Infected": "crit",
    "Suspicious": "warn",
    "NotScanned": "warn",
}


def get_malware_state(malware_status: str, params: Mapping[str, Any]) -> State:
    """Get the Checkmk State for a malware status based on params or defaults.

    Args:
        malware_status: The malware status string from the API.
        params: Check parameters with optional malware_status_states override.

    Returns:
        Checkmk State (OK, WARN, or CRIT).
    """
    state_map = {"ok": State.OK, "warn": State.WARN, "crit": State.CRIT}

    # Get configured overrides
    malware_states = params.get("malware_status_states", {})

    # Start with defaults and apply overrides
    effective_mapping: dict[str, State] = {
        "Clean": State.OK,
        "Infected": State.CRIT,
        "Suspicious": State.WARN,
        "NotScanned": State.WARN,
    }
    for status, state_str in malware_states.items():
        if state_str in state_map:
            effective_mapping[status] = state_map[state_str]

    return effective_mapping.get(malware_status, State.OK)


def yield_backup_metrics(
    data: Mapping[str, Any],
    params: Mapping[str, Any],
    restore_point_count: int,
    include_extra_metrics: bool = False,
) -> CheckResult:
    """Yield common backup check results and metrics.

    This shared function handles the common check logic for both
    veeam_rest_backup_objects and veeam_rest_vm_backup plugins.

    Args:
        data: The backup object/section data dict.
        params: Check parameters from ruleset.
        restore_point_count: Number of restore points.
        include_extra_metrics: If True, include additional metrics (avg_speed, etc.).

    Yields:
        Result and Metric objects for the check.
    """
    # --- Restore Points Metrics and Thresholds ---
    yield Metric("veeam_rest_backup_restore_points", restore_point_count)

    # Check minimum restore points
    min_warn = params.get("restore_points_min_warn")
    min_crit = params.get("restore_points_min_crit")
    if min_warn is not None and min_crit is not None:
        yield from check_levels(
            restore_point_count,
            levels_lower=("fixed", (min_warn, min_crit)),
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
            levels_upper=("fixed", (max_warn, max_crit)),
            render_func=lambda x: str(int(x)),
            label="Restore points",
            notice_only=True,
        )

    # --- Warning Info from Task Sessions ---
    warning_info = data.get("warningInfo")
    if warning_info:
        warning_title = warning_info.get("warningTitle", "Unknown")
        warning_msg = warning_info.get("warningMessage", "")
        warning_job = warning_info.get("jobName", "")
        severity = warning_info.get("severity", "Warning")

        issue_state = State.CRIT if severity == "Failed" else State.WARN
        issue_label = "Job error" if severity == "Failed" else "Job warning"

        yield Result(state=issue_state, summary=f"{issue_label}: {warning_title}")
        if warning_msg:
            yield Result(state=State.OK, notice=f"{severity} details: {warning_msg}")
        if warning_job:
            yield Result(state=State.OK, notice=f"{severity} from job: {warning_job}")

    # --- Backup Age ---
    backup_age = data.get("backupAgeSeconds")
    if backup_age is not None:
        age_warn_hours = params.get("backup_age_warn")
        age_crit_hours = params.get("backup_age_crit")

        # Convert hours to seconds for comparison
        levels = None
        if age_warn_hours and age_crit_hours:
            levels = ("fixed", (age_warn_hours * 3600, age_crit_hours * 3600))

        yield from check_levels(
            backup_age,
            levels_upper=levels,
            metric_name="veeam_rest_backup_age",
            render_func=render.timespan,
            label="Backup age",
        )

    # --- Task Data (VM backups only) ---
    task_data = data.get("taskData")
    if task_data:
        progress = task_data.get("progress") or {}

        # Processed size
        processed_size = progress.get("processedSize")
        if processed_size is not None:
            yield Result(state=State.OK, summary=f"Processed: {render.bytes(processed_size)}")
            yield Metric("veeam_rest_backup_size_processed", processed_size)

        # Duration
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

        # Additional size metrics
        read_size = progress.get("readSize")
        if read_size is not None:
            yield Metric("veeam_rest_backup_size_read", read_size)

        transferred_size = progress.get("transferredSize")
        if transferred_size is not None:
            yield Metric("veeam_rest_backup_size_transferred", transferred_size)

        # Extra metrics (only for backup_objects)
        if include_extra_metrics:
            avg_speed = progress.get("avgSpeed")
            if avg_speed is not None:
                yield Metric("veeam_rest_backup_avg_speed", avg_speed)

            total_size = progress.get("totalSize")
            if total_size is not None:
                yield Metric("veeam_rest_backup_total_size", total_size)

    # --- Latest Restore Point ---
    latest_rp = data.get("latestRestorePoint")
    if latest_rp:
        # Malware status
        malware_status = latest_rp.get("malwareStatus")
        if malware_status:
            status_state = get_malware_state(malware_status, params)
            yield Result(state=status_state, summary=f"Malware scan: {malware_status}")

        # Size from restore point (fallback if no task data)
        if not task_data or not (task_data.get("progress") or {}).get("processedSize"):
            original_size = latest_rp.get("originalSize")
            if original_size is not None:
                yield Result(state=State.OK, summary=f"Size: {render.bytes(original_size)}")
                yield Metric("veeam_rest_backup_size_processed", original_size)

        # Creation time
        creation_time = latest_rp.get("creationTime")
        if creation_time:
            yield Result(state=State.OK, notice=f"Last backup: {creation_time}")

        # Extra metrics from restore point (only for backup_objects)
        if include_extra_metrics:
            backup_size = latest_rp.get("backupSize")
            if backup_size is not None:
                yield Metric("veeam_rest_backup_backup_size", backup_size)

            data_size = latest_rp.get("dataSize")
            if data_size is not None:
                yield Metric("veeam_rest_backup_data_size", data_size)

    # --- Backup Server Info ---
    backup_server = data.get("backupServer")
    if backup_server:
        yield Result(state=State.OK, notice=f"Backup server: {backup_server}")
