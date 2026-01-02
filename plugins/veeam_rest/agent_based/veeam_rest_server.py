#!/usr/bin/env python3
"""
Check plugin for Veeam Backup Server Information.

Monitors backup server build, patches, and database information.
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

Section = dict[str, Any]


def parse_veeam_rest_server(string_table: StringTable) -> Section | None:
    """Parse JSON output from special agent."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_server = AgentSection(
    name="veeam_rest_server",
    parse_function=parse_veeam_rest_server,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_server(section: Section) -> DiscoveryResult:
    """Discover Veeam backup server."""
    if section:
        yield Service()


# =============================================================================
# CHECK FUNCTION
# =============================================================================

def check_veeam_rest_server(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check Veeam backup server information."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No server data received")
        return

    # Extract server properties
    server_name = section.get("name", "Unknown")
    build_version = section.get("buildVersion", "Unknown")
    vbr_id = section.get("vbrId", "")
    patches = section.get("patches", [])
    database_vendor = section.get("databaseVendor", "")
    sql_edition = section.get("sqlServerEdition", "")
    sql_version = section.get("sqlServerVersion", "")
    platform = section.get("platform", "")

    # Main summary
    yield Result(
        state=State.OK,
        summary=f"Version: {build_version}, Server: {server_name}",
    )

    # Check for patches
    if patches:
        patch_count = len(patches)
        patch_list = ", ".join(patches[-3:])  # Show last 3 patches
        if patch_count > 3:
            patch_list = f"...{patch_list}"
        yield Result(
            state=State.OK,
            summary=f"Patches installed: {patch_count}",
        )
        yield Result(
            state=State.OK,
            notice=f"Latest patches: {patch_list}",
        )
    else:
        yield Result(
            state=State.OK,
            notice="No patches installed",
        )

    # Database details
    if database_vendor:
        db_info = f"Database: {database_vendor}"
        if sql_edition:
            db_info += f" ({sql_edition})"
        if sql_version:
            db_info += f" v{sql_version}"
        yield Result(state=State.OK, notice=db_info)

    # Platform info
    if platform:
        yield Result(state=State.OK, notice=f"Platform: {platform}")

    # Installation ID
    if vbr_id:
        yield Result(state=State.OK, notice=f"Installation ID: {vbr_id}")


check_plugin_veeam_rest_server = CheckPlugin(
    name="veeam_rest_server",
    service_name="Veeam Backup Server",
    discovery_function=discover_veeam_rest_server,
    check_function=check_veeam_rest_server,
    check_default_parameters={},
    check_ruleset_name="veeam_rest_server",
)
