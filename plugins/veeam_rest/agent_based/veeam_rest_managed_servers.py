#!/usr/bin/env python3
"""
Check plugin for Veeam Managed Servers.

Monitors managed server status (vCenter, ESXi, Hyper-V hosts, etc.).
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


def parse_veeam_rest_managed_servers(string_table: StringTable) -> Section | None:
    """Parse JSON output from special agent."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_managed_servers = AgentSection(
    name="veeam_rest_managed_servers",
    parse_function=parse_veeam_rest_managed_servers,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_managed_servers(section: Section) -> DiscoveryResult:
    """Discover managed servers."""
    if not section:
        return

    for server in section:
        server_name = server.get("name")
        if server_name:
            yield Service(item=server_name)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

SERVER_TYPE_MAP = {
    "WindowsHost": "Windows Host",
    "LinuxHost": "Linux Host",
    "ViHost": "VMware vSphere",
    "CloudDirectorHost": "VMware Cloud Director",
    "HvServer": "Hyper-V Server",
    "HvCluster": "Hyper-V Cluster",
    "SCVMM": "System Center VMM",
    "SmbV3Cluster": "SMB Cluster",
    "SmbV3StandaloneHost": "SMB Host",
}

# Status values that indicate problems
PROBLEM_STATUSES = {
    "Unavailable": State.CRIT,
    "Inaccessible": State.CRIT,
    "Offline": State.CRIT,
    "Maintenance": State.WARN,
    "Warning": State.WARN,
}


def check_veeam_rest_managed_servers(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check a single managed server."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # Find the server by name
    server = None
    for s in section:
        if s.get("name") == item:
            server = s
            break

    if server is None:
        yield Result(state=State.UNKNOWN, summary="Server not found")
        return

    # Extract server properties
    server_type = server.get("type", "Unknown")
    status = server.get("status", "Unknown")
    description = server.get("description", "")

    # Determine state based on status
    state = PROBLEM_STATUSES.get(status, State.OK)

    # Build summary
    server_type_display = SERVER_TYPE_MAP.get(server_type, server_type)
    summary = f"{server_type_display}: {status}"

    yield Result(state=state, summary=summary)

    # Additional properties for details
    server_id = server.get("id", "")
    is_backup_server = server.get("isBackupServer", False)
    is_default_mount_server = server.get("isDefaultMountServer", False)
    credentials_storage = server.get("credentialsStorageType", "")
    network_settings = server.get("networkSettings", {})

    # Details section
    yield Result(state=State.OK, notice=f"Type: {server_type}")

    if description:
        yield Result(state=State.OK, notice=f"Description: {description}")

    # Role flags
    roles = []
    if is_backup_server:
        roles.append("Backup Server")
    if is_default_mount_server:
        roles.append("Default Mount Server")
    if roles:
        yield Result(state=State.OK, notice=f"Roles: {', '.join(roles)}")

    if credentials_storage:
        yield Result(state=State.OK, notice=f"Credentials Storage: {credentials_storage}")

    # Network settings
    if network_settings:
        port_range_start = network_settings.get("portRangeStart", 0)
        port_range_end = network_settings.get("portRangeEnd", 0)
        if port_range_start and port_range_end:
            yield Result(state=State.OK, notice=f"Port Range: {port_range_start}-{port_range_end}")

        # List active components
        components = network_settings.get("components", [])
        active_components = [
            f"{c['componentName']}:{c['port']}"
            for c in components
            if c.get("port", -1) > 0
        ]
        if active_components:
            yield Result(state=State.OK, notice=f"Components: {', '.join(active_components)}")

    if server_id:
        yield Result(state=State.OK, notice=f"Server ID: {server_id}")


check_plugin_veeam_rest_managed_servers = CheckPlugin(
    name="veeam_rest_managed_servers",
    service_name="Veeam Server %s",
    discovery_function=discover_veeam_rest_managed_servers,
    check_function=check_veeam_rest_managed_servers,
    check_default_parameters={},
)
