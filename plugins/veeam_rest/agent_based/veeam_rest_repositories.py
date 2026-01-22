#!/usr/bin/env python3
"""
Check plugin for Veeam Backup Repositories.

Monitors repository capacity, usage, and online status.
"""

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
    check_levels,
    render,
)

from cmk_addons.plugins.veeam_rest.lib import parse_json_section


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = dict[str, dict[str, Any]]  # "Category - Name" -> repository data


def _get_repo_item(repo: dict[str, Any]) -> str | None:
    """Get the service item name for a repository."""
    name = repo.get("name")
    if not name:
        return None
    category = _get_repo_category(repo)
    return f"{category} - {name}"


def parse_veeam_rest_repositories(string_table) -> Section | None:
    """Parse JSON list of repositories into dict by 'Category - Name' for O(1) lookup."""
    data = parse_json_section(string_table)
    if not data or not isinstance(data, list):
        return None
    result = {}
    for repo in data:
        item = _get_repo_item(repo)
        if item:
            result[item] = repo
    return result or None


agent_section_veeam_rest_repositories = AgentSection(
    name="veeam_rest_repositories",
    parse_function=parse_veeam_rest_repositories,
)


# =============================================================================
# TYPE MAPPING
# =============================================================================

# Map API repository types to human-readable category prefixes
REPO_TYPE_CATEGORY = {
    # Local repositories
    "WinLocal": "Local",
    "LinuxLocal": "Local",
    "LinuxHardened": "Hardened",
    # Network shares
    "Smb": "SMB",
    "Nfs": "NFS",
    # Cloud storage
    "AzureBlob": "Azure",
    "AzureDataBox": "Azure DataBox",
    "AzureArchive": "Azure Archive",
    "AmazonS3": "S3",
    "AmazonSnowballEdge": "Snowball",
    "AmazonS3Glacier": "Glacier",
    "S3Compatible": "S3",
    "S3GlacierCompatible": "S3 Glacier",
    "GoogleCloud": "GCS",
    "IBMCloud": "IBM Cloud",
    "WasabiCloud": "Wasabi",
    "VeeamDataCloudVault": "Veeam Cloud",
    "SmartObjectS3": "S3",
    "Cloud": "Cloud",
    # Deduplication appliances
    "DDBoost": "DataDomain",
    "ExaGrid": "ExaGrid",
    "HPStoreOnceIntegration": "StoreOnce",
    "HPStoreOnce": "StoreOnce",
    "Quantum": "Quantum",
    "Infinidat": "Infinidat",
    "Fujitsu": "Fujitsu",
    # Other
    "ExtendableRepository": "Extendable",
}


def _get_repo_category(repo: dict[str, Any]) -> str:
    """Determine the repository category for service naming."""
    # Check if this is a scale-out extent
    if repo.get("scaleOutRepositoryDetails"):
        extent_type = repo["scaleOutRepositoryDetails"].get("extentType", "")
        if extent_type == "Performance":
            return "SOBR Extent"
        elif extent_type == "Capacity":
            return "SOBR Capacity"
        elif extent_type == "Archive":
            return "SOBR Archive"
        return "SOBR Extent"

    # Get type from mapping or use raw type
    repo_type = repo.get("type", "Unknown")
    return REPO_TYPE_CATEGORY.get(repo_type, repo_type)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_repositories(section: Section) -> DiscoveryResult:
    """Discover backup repositories."""
    if not section:
        return

    for item in section:
        yield Service(item=item)


# =============================================================================
# CHECK FUNCTION
# =============================================================================

def check_veeam_rest_repositories(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check a single backup repository."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # O(1) lookup by "Category - Name"
    repo = section.get(item)
    if repo is None:
        yield Result(state=State.UNKNOWN, summary="Repository not found")
        return

    # Extract repository properties
    repo_type = repo.get("type", "Unknown")
    capacity_gb = repo.get("capacityGB", 0)
    free_gb = repo.get("freeGB", 0)
    # Note: usedSpaceGB from API can be incorrect (shows logical data size, not actual disk usage)
    # Calculate actual used space from capacity - free for accurate percentage
    used_gb = capacity_gb - free_gb if capacity_gb > 0 else 0
    is_online = repo.get("isOnline", True)
    is_outdated = repo.get("isOutOfDate", False)
    host_name = repo.get("hostName", "")
    path = repo.get("path", "")

    # Convert to bytes for metrics
    capacity_bytes = capacity_gb * 1024 * 1024 * 1024
    free_bytes = free_gb * 1024 * 1024 * 1024
    used_bytes = used_gb * 1024 * 1024 * 1024

    # Calculate usage percentage
    if capacity_gb > 0:
        used_percent = (used_gb / capacity_gb) * 100
    else:
        used_percent = 0

    # Check online status
    if not is_online:
        yield Result(state=State.CRIT, summary="Repository is OFFLINE")
        return

    # Check outdated components
    if is_outdated:
        yield Result(state=State.WARN, summary="Repository has outdated components")

    # Check usage levels
    usage_levels = params.get("usage_levels")
    if usage_levels:
        # Handle both formats: ("fixed", (w, c)) and bare (w, c)
        if isinstance(usage_levels, tuple) and len(usage_levels) == 2:
            if isinstance(usage_levels[0], str):
                # Already in ("fixed", (w, c)) format
                levels = usage_levels
            else:
                # Bare (w, c) format - wrap it
                levels = ("fixed", usage_levels)
        else:
            levels = usage_levels
        yield from check_levels(
            used_percent,
            levels_upper=levels,
            metric_name="repository_used_percent",
            label="Used",
            render_func=render.percent,
            boundaries=(0, 100),
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"Used: {render.percent(used_percent)}",
        )
        yield Metric("veeam_rest_repository_used_percent", used_percent, boundaries=(0, 100))

    # Check free space levels (lower threshold - alert when free space is LOW)
    free_space_levels = params.get("free_space_levels")
    if free_space_levels:
        # Handle both formats: ("fixed", (w, c)) and bare (w, c)
        if isinstance(free_space_levels, tuple) and len(free_space_levels) == 2:
            if isinstance(free_space_levels[0], str):
                # ("fixed", (warn_bytes, crit_bytes)) format
                levels = free_space_levels
            else:
                # Legacy bare (warn_gb, crit_gb) format - convert to bytes
                warn_bytes_threshold = free_space_levels[0] * 1024 * 1024 * 1024
                crit_bytes_threshold = free_space_levels[1] * 1024 * 1024 * 1024
                levels = ("fixed", (warn_bytes_threshold, crit_bytes_threshold))
        else:
            levels = free_space_levels

        yield from check_levels(
            free_bytes,
            levels_lower=levels,
            metric_name="veeam_rest_repository_free",
            label="Free",
            render_func=render.disksize,
        )

    # Capacity info
    yield Result(
        state=State.OK,
        summary=f"Capacity: {render.disksize(capacity_bytes)}, Free: {render.disksize(free_bytes)}",
    )

    # Metrics (repository_free may already be yielded by check_levels above)
    yield Metric("veeam_rest_repository_capacity", capacity_bytes)
    if not free_space_levels:
        yield Metric("veeam_rest_repository_free", free_bytes)
    yield Metric("veeam_rest_repository_used", used_bytes)

    # Additional properties for details
    description = repo.get("description", "")
    repo_id = repo.get("id", "")
    scaleout_details = repo.get("scaleOutRepositoryDetails", {})

    # Details section
    yield Result(state=State.OK, notice=f"Type: {repo_type}")

    if host_name:
        yield Result(state=State.OK, notice=f"Host: {host_name}")

    if path:
        yield Result(state=State.OK, notice=f"Path: {path}")

    if description:
        yield Result(state=State.OK, notice=f"Description: {description}")

    # Scale-out repository details
    if scaleout_details:
        extent_type = scaleout_details.get("extentType", "")
        membership = scaleout_details.get("membership", "")
        if extent_type:
            yield Result(state=State.OK, notice=f"Extent Type: {extent_type}")
        if membership:
            yield Result(state=State.OK, notice=f"Member of: {membership}")

    if repo_id:
        yield Result(state=State.OK, notice=f"ID: {repo_id}")


check_plugin_veeam_rest_repositories = CheckPlugin(
    name="veeam_rest_repositories",
    service_name="Veeam Repository %s",
    discovery_function=discover_veeam_rest_repositories,
    check_function=check_veeam_rest_repositories,
    check_default_parameters={
        "usage_levels": ("fixed", (80.0, 90.0)),  # Warn at 80%, Crit at 90%
    },
    check_ruleset_name="veeam_rest_repositories",
)
