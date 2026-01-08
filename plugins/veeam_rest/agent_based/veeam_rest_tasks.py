#!/usr/bin/env python3
"""
Check plugin for Veeam Task Sessions (per-VM backup details).

This replaces the veeam_client section from the PowerShell plugin,
providing per-VM/object backup details with performance metrics.
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


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = list[dict[str, Any]]


def parse_veeam_rest_tasks(string_table: StringTable) -> Section | None:
    """Parse JSON output from special agent."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_tasks = AgentSection(
    name="veeam_rest_tasks",
    parse_function=parse_veeam_rest_tasks,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_tasks(section: Section) -> DiscoveryResult:
    """Discover task sessions (VMs/objects)."""
    if not section:
        return

    # Group by object name and find the most recent task for each
    latest_tasks: dict[str, dict] = {}

    for task in section:
        name = task.get("name")
        if not name:
            continue

        # Use the most recent task per object
        end_time = task.get("endTime") or task.get("creationTime") or ""
        if name not in latest_tasks or end_time > latest_tasks[name].get("endTime", ""):
            latest_tasks[name] = task

    for name in latest_tasks:
        yield Service(item=name)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

RESULT_STATE_MAP = {
    "Success": State.OK,
    "Warning": State.WARN,
    "Failed": State.CRIT,
    "None": State.OK,
}

STATE_MAP = {
    "Stopped": "completed",
    "Working": "running",
    "Starting": "starting",
    "Stopping": "stopping",
    "Pausing": "pausing",
    "Resuming": "resuming",
    "WaitingTape": "waiting for tape",
    "Idle": "idle",
    "Postprocessing": "postprocessing",
    "WaitingRepository": "waiting for repository",
    "WaitingSlot": "waiting for slot",
}


def _format_duration_hms(seconds: int) -> str:
    """Format duration as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _get_latest_task(item: str, section: Section) -> dict | None:
    """Find the most recent task for an item."""
    latest_task = None
    latest_time = ""

    for task in section:
        if task.get("name") != item:
            continue

        end_time = task.get("endTime") or task.get("creationTime") or ""
        if end_time > latest_time:
            latest_time = end_time
            latest_task = task

    return latest_task


def check_veeam_rest_tasks(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check a single task session (VM/object)."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    task = _get_latest_task(item, section)
    if task is None:
        yield Result(state=State.UNKNOWN, summary="Task not found")
        return

    # Extract task properties
    state_str = task.get("state", "Unknown")
    result_obj = task.get("result", {})
    result_str = result_obj.get("result", "None") if isinstance(result_obj, dict) else "None"
    result_message = result_obj.get("message") if isinstance(result_obj, dict) else None

    creation_time = task.get("creationTime", "")
    end_time = task.get("endTime", "")
    backup_age = task.get("backupAgeSeconds")
    duration_seconds = task.get("durationSeconds")

    progress = task.get("progress", {}) or {}
    processed_size = progress.get("processedSize")
    read_size = progress.get("readSize")
    transferred_size = progress.get("transferredSize")
    processing_rate = progress.get("processingRate", "")
    bottleneck = progress.get("bottleneck", "Unknown")
    progress_percent = progress.get("progressPercent", 0)

    # Determine check state
    check_state = RESULT_STATE_MAP.get(result_str, State.UNKNOWN)

    # Build summary
    state_text = STATE_MAP.get(state_str, state_str.lower())
    summary_parts = [f"State: {state_text}", f"Result: {result_str}"]

    if state_str == "Working":
        summary_parts.append(f"Progress: {progress_percent}%")
        check_state = State.OK  # Running is OK
    else:
        # Add duration and processed size for completed tasks
        if duration_seconds is not None:
            summary_parts.append(f"Last Duration: {_format_duration_hms(duration_seconds)}")
        if processed_size is not None:
            summary_parts.append(f"Processed: {render.bytes(processed_size)}")

    yield Result(state=check_state, summary=", ".join(summary_parts))

    # Check backup age
    max_age = params.get("max_backup_age")
    if max_age is not None and backup_age is not None and state_str == "Stopped":
        max_age_seconds = max_age * 3600
        if backup_age > max_age_seconds:
            age_text = render.timespan(backup_age)
            yield Result(
                state=State.WARN,
                summary=f"Last backup {age_text} ago exceeds threshold of {max_age}h",
            )

    # Check duration
    max_duration = params.get("max_duration")
    if max_duration is not None and duration_seconds is not None:
        max_duration_seconds = max_duration * 3600
        if duration_seconds > max_duration_seconds:
            duration_text = render.timespan(duration_seconds)
            yield Result(
                state=State.WARN,
                summary=f"Duration {duration_text} exceeds threshold of {max_duration}h",
            )

    # Metrics
    if backup_age is not None:
        yield Metric("backup_age", backup_age)

    if duration_seconds is not None:
        yield Metric("backup_duration", duration_seconds)

    if processed_size is not None:
        yield Metric("backup_size_processed", processed_size)

    if read_size is not None:
        yield Metric("backup_size_read", read_size)

    if transferred_size is not None:
        yield Metric("backup_size_transferred", transferred_size)

    # Details
    details_parts = []

    if duration_seconds is not None:
        details_parts.append(f"Duration: {render.timespan(duration_seconds)}")

    if processed_size is not None:
        details_parts.append(f"Processed: {render.bytes(processed_size)}")

    if read_size is not None:
        details_parts.append(f"Read: {render.bytes(read_size)}")

    if transferred_size is not None:
        details_parts.append(f"Transferred: {render.bytes(transferred_size)}")

    if processing_rate:
        details_parts.append(f"Speed: {processing_rate}")

    if bottleneck and bottleneck != "Unknown":
        details_parts.append(f"Bottleneck: {bottleneck}")

    if creation_time:
        details_parts.append(f"Started: {creation_time}")

    if end_time:
        details_parts.append(f"Ended: {end_time}")

    if result_message:
        details_parts.append(f"Message: {result_message}")

    if details_parts:
        yield Result(state=State.OK, notice=", ".join(details_parts))


check_plugin_veeam_rest_tasks = CheckPlugin(
    name="veeam_rest_tasks",
    service_name="Veeam Backup %s",
    discovery_function=discover_veeam_rest_tasks,
    check_function=check_veeam_rest_tasks,
    check_default_parameters={},  # No defaults - thresholds are optional
    check_ruleset_name="veeam_rest_tasks",
)
