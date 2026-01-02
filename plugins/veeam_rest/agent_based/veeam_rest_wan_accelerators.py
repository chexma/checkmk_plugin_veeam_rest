#!/usr/bin/env python3
"""
Check plugin for Veeam WAN Accelerators.

Monitors WAN accelerator status and cache configuration.
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
    render,
)


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = list[dict[str, Any]]


def parse_veeam_rest_wan_accelerators(string_table: StringTable) -> Section | None:
    """Parse JSON output from special agent."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_wan_accelerators = AgentSection(
    name="veeam_rest_wan_accelerators",
    parse_function=parse_veeam_rest_wan_accelerators,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_wan_accelerators(section: Section) -> DiscoveryResult:
    """Discover WAN accelerators."""
    if not section:
        return

    for accelerator in section:
        name = accelerator.get("name")
        if name:
            yield Service(item=name)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

# Cache size unit multipliers (to bytes)
CACHE_SIZE_UNITS = {
    "Gigabyte": 1024 * 1024 * 1024,
    "Megabyte": 1024 * 1024,
    "Terabyte": 1024 * 1024 * 1024 * 1024,
}


def check_veeam_rest_wan_accelerators(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check a single WAN accelerator."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # Find the WAN accelerator by name
    accelerator = None
    for a in section:
        if a.get("name") == item:
            accelerator = a
            break

    if accelerator is None:
        yield Result(state=State.UNKNOWN, summary="WAN accelerator not found")
        return

    # Extract properties
    server = accelerator.get("server", {})
    cache = accelerator.get("cache", {})

    # Server properties
    description = server.get("description", "")
    traffic_port = server.get("trafficPort", 0)
    streams_count = server.get("streamsCount", 0)
    high_bandwidth_mode = server.get("highBandwidthModeEnabled", False)

    # Cache properties
    cache_folder = cache.get("cacheFolder", "")
    cache_size = cache.get("cacheSize", 0)
    cache_size_unit = cache.get("cacheSizeUnit", "Gigabyte")

    # Calculate cache size in bytes
    cache_size_bytes = cache_size * CACHE_SIZE_UNITS.get(cache_size_unit, 1024 * 1024 * 1024)

    # WAN accelerator is considered OK if it exists in the API response
    yield Result(
        state=State.OK,
        summary=f"Cache: {render.disksize(cache_size_bytes)}",
    )

    # Report configuration
    if high_bandwidth_mode:
        yield Result(state=State.OK, summary="High bandwidth mode: enabled")

    if streams_count > 0:
        yield Result(state=State.OK, notice=f"Streams: {streams_count}")

    if traffic_port:
        yield Result(state=State.OK, notice=f"Traffic port: {traffic_port}")

    if cache_folder:
        yield Result(state=State.OK, notice=f"Cache folder: {cache_folder}")

    if description:
        yield Result(state=State.OK, notice=f"Description: {description}")

    # Metrics
    yield Metric("wan_accelerator_cache_size", cache_size_bytes)
    if streams_count > 0:
        yield Metric("wan_accelerator_streams", streams_count)


check_plugin_veeam_rest_wan_accelerators = CheckPlugin(
    name="veeam_rest_wan_accelerators",
    service_name="Veeam WAN Accelerator %s",
    discovery_function=discover_veeam_rest_wan_accelerators,
    check_function=check_veeam_rest_wan_accelerators,
    check_default_parameters={},
    check_ruleset_name="veeam_rest_wan_accelerators",
)
