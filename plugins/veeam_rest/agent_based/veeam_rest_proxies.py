#!/usr/bin/env python3
"""
Check plugin for Veeam Backup Proxies.

Monitors proxy online status and configuration.
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

Section = dict[str, dict[str, Any]]  # name -> proxy data


def parse_veeam_rest_proxies(string_table) -> Section | None:
    """Parse JSON list of proxies into dict by name for O(1) lookup."""
    data = parse_json_section(string_table)
    if not data or not isinstance(data, list):
        return None
    return {p.get("name"): p for p in data if p.get("name")} or None


agent_section_veeam_rest_proxies = AgentSection(
    name="veeam_rest_proxies",
    parse_function=parse_veeam_rest_proxies,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_proxies(section: Section) -> DiscoveryResult:
    """Discover backup proxies."""
    if not section:
        return

    for name in section:
        yield Service(item=name)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

PROXY_TYPE_MAP = {
    "ViProxy": "VMware vSphere",
    "HvProxy": "Microsoft Hyper-V",
    "GeneralPurposeProxy": "General Purpose",
}


def check_veeam_rest_proxies(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check a single backup proxy."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # O(1) lookup by name
    proxy = section.get(item)
    if proxy is None:
        yield Result(state=State.UNKNOWN, summary="Proxy not found")
        return

    # Extract proxy properties
    proxy_type = proxy.get("type", "Unknown")
    host_name = proxy.get("hostName", "")
    is_online = proxy.get("isOnline", True)
    is_disabled = proxy.get("isDisabled", False)
    is_outdated = proxy.get("isOutOfDate", False)
    description = proxy.get("description", "")

    # Determine state based on status
    state = State.OK
    status_parts = []

    if not is_online:
        state = State.CRIT
        status_parts.append("OFFLINE")
    else:
        status_parts.append("online")

    if is_disabled:
        if state == State.OK:
            state = State.WARN
        status_parts.append("disabled")

    if is_outdated:
        if state == State.OK:
            state = State.WARN
        status_parts.append("outdated components")

    # Build summary
    proxy_type_display = PROXY_TYPE_MAP.get(proxy_type, proxy_type)
    summary = f"{proxy_type_display} proxy: {', '.join(status_parts)}"

    yield Result(state=state, summary=summary)

    # Additional properties for details
    proxy_id = proxy.get("id", "")
    host_id = proxy.get("hostId", "")

    # Details section
    yield Result(state=State.OK, notice=f"Type: {proxy_type}")

    if host_name:
        yield Result(state=State.OK, notice=f"Host: {host_name}")

    if description:
        yield Result(state=State.OK, notice=f"Description: {description}")

    # Status flags
    status_flags = []
    if is_online:
        status_flags.append("Online")
    else:
        status_flags.append("Offline")
    if is_disabled:
        status_flags.append("Disabled")
    if is_outdated:
        status_flags.append("Outdated")
    yield Result(state=State.OK, notice=f"Status Flags: {', '.join(status_flags)}")

    if proxy_id:
        yield Result(state=State.OK, notice=f"Proxy ID: {proxy_id}")

    if host_id:
        yield Result(state=State.OK, notice=f"Host ID: {host_id}")


check_plugin_veeam_rest_proxies = CheckPlugin(
    name="veeam_rest_proxies",
    service_name="Veeam Proxy %s",
    discovery_function=discover_veeam_rest_proxies,
    check_function=check_veeam_rest_proxies,
    check_default_parameters={},
    check_ruleset_name="veeam_rest_proxies",
)
