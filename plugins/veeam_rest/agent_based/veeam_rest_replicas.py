#!/usr/bin/env python3
"""
Check plugin for Veeam Replicas.

Monitors replica status for disaster recovery.
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

from cmk_addons.plugins.veeam_rest.lib import parse_json_section


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = dict[str, dict[str, Any]]  # name -> replica data


def parse_veeam_rest_replicas(string_table) -> Section | None:
    """Parse JSON list of replicas into dict by name for O(1) lookup."""
    data = parse_json_section(string_table)
    if not data or not isinstance(data, list):
        return None
    return {r.get("name"): r for r in data if r.get("name")} or None


agent_section_veeam_rest_replicas = AgentSection(
    name="veeam_rest_replicas",
    parse_function=parse_veeam_rest_replicas,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_replicas(section: Section) -> DiscoveryResult:
    """Discover replicas."""
    if not section:
        return

    for name in section:
        yield Service(item=name)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

PLATFORM_MAP = {
    "VMware": "vSphere",
    "HyperV": "Hyper-V",
}


def check_veeam_rest_replicas(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check a single replica."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # O(1) lookup by name
    replica = section.get(item)
    if replica is None:
        yield Result(state=State.UNKNOWN, summary="Replica not found")
        return

    # Extract replica properties
    replica_type = replica.get("type", "Regular")
    platform = replica.get("platformName", "Unknown")
    job_id = replica.get("jobId", "")

    # Determine state - replicas are OK if they exist
    state = State.OK

    # Build summary
    platform_display = PLATFORM_MAP.get(platform, platform)
    summary = f"{platform_display} replica: OK"

    yield Result(state=state, summary=summary)

    # Details section
    yield Result(state=State.OK, notice=f"Type: {replica_type}")
    yield Result(state=State.OK, notice=f"Platform: {platform}")

    if job_id:
        yield Result(state=State.OK, notice=f"Job ID: {job_id}")

    replica_id = replica.get("id", "")
    if replica_id:
        yield Result(state=State.OK, notice=f"Replica ID: {replica_id}")


check_plugin_veeam_rest_replicas = CheckPlugin(
    name="veeam_rest_replicas",
    service_name="Veeam Replica %s",
    discovery_function=discover_veeam_rest_replicas,
    check_function=check_veeam_rest_replicas,
    check_default_parameters={},
)
