#!/usr/bin/env python3
"""
Check plugin for Veeam VM/Agent Backup status via piggyback.

This check receives backup status data attached to monitored VMs/computers
via Checkmk's piggyback mechanism. Data comes from the backupObjects API.
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
        yield Service()


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

    summary = f"{result_text}, Type: {type_display}"
    if platform:
        summary += f" ({platform})"
    summary += f", Restore points: {restore_point_count}"

    yield Result(state=result_state, summary=summary)

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

    # Latest restore point details
    latest_rp = section.get("latestRestorePoint")
    if latest_rp:
        # Size from restore point
        original_size = latest_rp.get("originalSize")
        if original_size is not None:
            yield Result(state=State.OK, summary=f"Size: {render.bytes(original_size)}")
            yield Metric("veeam_rest_backup_size_processed", original_size)

        # Malware status
        malware_status = latest_rp.get("malwareStatus")
        if malware_status and malware_status != "NotScanned":
            if malware_status == "Clean":
                yield Result(state=State.OK, notice="Malware scan: Clean")
            elif malware_status == "Infected":
                yield Result(state=State.CRIT, summary="Malware detected!")
            else:
                yield Result(state=State.OK, notice=f"Malware scan: {malware_status}")

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
    service_name="Veeam Backup",
    discovery_function=discover_veeam_rest_vm_backup,
    check_function=check_veeam_rest_vm_backup,
    check_default_parameters={},
    check_ruleset_name="veeam_rest_vm_backup",
)
