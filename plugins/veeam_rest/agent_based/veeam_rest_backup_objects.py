#!/usr/bin/env python3
"""
Check plugin for Veeam Backup Objects as services on the Veeam server.

This check creates individual services for each backup object (VM, agent backup)
directly on the Veeam server. Alternative to piggyback mode.
"""

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

from cmk_addons.plugins.veeam_rest.lib import parse_json_section, yield_backup_metrics


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = dict[str, dict[str, Any]]  # name -> object data


def parse_veeam_rest_backup_objects(string_table: StringTable) -> Section | None:
    """Parse JSON list of backup objects into dict by name for O(1) lookup."""
    data = parse_json_section(string_table)
    if not data or not isinstance(data, list):
        return None
    return {obj.get("name"): obj for obj in data if obj.get("name")} or None


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

    # Yield common backup metrics and checks (restore points, age, task data, malware, etc.)
    yield from yield_backup_metrics(obj, params, restore_point_count, include_extra_metrics=True)


check_plugin_veeam_rest_backup_objects = CheckPlugin(
    name="veeam_rest_backup_objects",
    service_name="Veeam Backup %s",
    discovery_function=discover_veeam_rest_backup_objects,
    check_function=check_veeam_rest_backup_objects,
    check_default_parameters={
        "malware_status_states": {},  # Use defaults: Clean=OK, Infected=CRIT, Suspicious=WARN, NotScanned=WARN
    },
    check_ruleset_name="veeam_rest_backup",
)
