#!/usr/bin/env python3
"""
Check plugin for Veeam VM/Agent Backup status via piggyback.

This check receives backup status data attached to monitored VMs/computers
via Checkmk's piggyback mechanism. Data comes from the backupObjects API,
enriched with task data for VM backups.
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
)

from cmk_addons.plugins.veeam_rest.lib import parse_json_section, yield_backup_metrics


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = dict[str, Any]


agent_section_veeam_rest_vm_backup = AgentSection(
    name="veeam_rest_vm_backup",
    parse_function=parse_json_section,
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

    # Yield common backup metrics and checks (restore points, age, task data, malware, etc.)
    yield from yield_backup_metrics(section, params, restore_point_count)


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
