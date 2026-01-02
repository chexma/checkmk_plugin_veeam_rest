#!/usr/bin/env python3
"""
Check plugin for Veeam Scale-Out Backup Repositories.

Monitors scale-out repository status and extent health.
"""

import json
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


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = list[dict[str, Any]]


def parse_veeam_rest_scaleout_repositories(string_table: StringTable) -> Section | None:
    """Parse JSON output from special agent."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_scaleout_repositories = AgentSection(
    name="veeam_rest_scaleout_repositories",
    parse_function=parse_veeam_rest_scaleout_repositories,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_scaleout_repositories(section: Section) -> DiscoveryResult:
    """Discover scale-out backup repositories."""
    if not section:
        return

    for repo in section:
        repo_name = repo.get("name")
        if repo_name:
            yield Service(item=repo_name)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

# Extent status state mapping
EXTENT_STATUS_STATE_MAP = {
    "Normal": State.OK,
    "Evacuate": State.WARN,
    "Pending": State.OK,
    "Sealed": State.OK,
    "Maintenance": State.WARN,
    "ResyncRequired": State.WARN,
    "TenantEvacuating": State.WARN,
}


def check_veeam_rest_scaleout_repositories(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check a single scale-out backup repository."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # Find the repository by name
    repo = None
    for r in section:
        if r.get("name") == item:
            repo = r
            break

    if repo is None:
        yield Result(state=State.UNKNOWN, summary="Repository not found")
        return

    # Extract repository properties
    description = repo.get("description", "")

    # Check performance tier (extents)
    performance_tier = repo.get("performanceTier", {})
    extents = performance_tier.get("performanceExtents", [])

    total_extents = len(extents)
    healthy_extents = 0
    extent_issues = []
    sealed_extents = []
    maintenance_extents = []

    for extent in extents:
        extent_name = extent.get("name", "Unknown")
        extent_statuses = extent.get("status", [])

        # Check if any status indicates an issue
        has_issue = False
        is_sealed = False
        is_maintenance = False

        for status in extent_statuses:
            if status == "Sealed":
                is_sealed = True
                sealed_extents.append(extent_name)
            elif status == "Maintenance":
                is_maintenance = True
                maintenance_extents.append(extent_name)
            elif status in ("Evacuate", "ResyncRequired", "TenantEvacuating"):
                has_issue = True
                extent_issues.append(f"{extent_name}: {status}")

        if not has_issue and not is_sealed and not is_maintenance:
            healthy_extents += 1
        elif is_sealed or is_maintenance:
            # Sealed/Maintenance are not counted as healthy but not critical
            pass

    # Report extent summary
    if total_extents == 0:
        yield Result(state=State.WARN, summary="No performance extents configured")
    else:
        if extent_issues:
            yield Result(
                state=State.WARN,
                summary=f"Extents: {healthy_extents}/{total_extents} healthy",
            )
            for issue in extent_issues:
                yield Result(state=State.WARN, summary=f"Extent issue: {issue}")
        else:
            yield Result(
                state=State.OK,
                summary=f"Extents: {healthy_extents}/{total_extents} healthy",
            )

    # Report sealed extents
    if sealed_extents:
        yield Result(
            state=State.OK,
            notice=f"Sealed extents: {', '.join(sealed_extents)}",
        )

    # Report maintenance extents
    if maintenance_extents:
        yield Result(
            state=State.WARN,
            summary=f"Maintenance mode: {', '.join(maintenance_extents)}",
        )

    # Check capacity tier
    capacity_tier = repo.get("capacityTier")
    if capacity_tier:
        capacity_enabled = capacity_tier.get("enabled", False)
        if capacity_enabled:
            offload_window = capacity_tier.get("offloadWindow", {})
            is_enabled = offload_window.get("enabled", False)
            yield Result(
                state=State.OK,
                notice=f"Capacity tier: enabled (offload {'active' if is_enabled else 'disabled'})",
            )

    # Check archive tier
    archive_tier = repo.get("archiveTier")
    if archive_tier:
        archive_enabled = archive_tier.get("enabled", False)
        if archive_enabled:
            yield Result(state=State.OK, notice="Archive tier: enabled")

    # Check placement policy
    placement_policy = repo.get("placementPolicy")
    if placement_policy:
        policy_type = placement_policy.get("type", "Unknown")
        yield Result(state=State.OK, notice=f"Placement policy: {policy_type}")

    # Description in details
    if description:
        yield Result(state=State.OK, notice=f"Description: {description}")


check_plugin_veeam_rest_scaleout_repositories = CheckPlugin(
    name="veeam_rest_scaleout_repositories",
    service_name="Veeam SOBR %s",
    discovery_function=discover_veeam_rest_scaleout_repositories,
    check_function=check_veeam_rest_scaleout_repositories,
    check_default_parameters={},
    check_ruleset_name="veeam_rest_scaleout_repositories",
)
