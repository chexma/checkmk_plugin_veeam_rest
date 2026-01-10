#!/usr/bin/env python3
"""
Check plugin for Veeam Backup License.

Monitors license status, expiration, and usage.
"""

import json
from collections.abc import Mapping
from datetime import datetime, timezone
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


def parse_veeam_rest_license(string_table: StringTable) -> Section | None:
    """Parse JSON output from special agent."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_license = AgentSection(
    name="veeam_rest_license",
    parse_function=parse_veeam_rest_license,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_license(section: Section) -> DiscoveryResult:
    """Discover Veeam license."""
    if section:
        yield Service()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_datetime(date_str: str | None) -> datetime | None:
    """Parse ISO 8601 datetime string to datetime object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _days_until(target_date: datetime | None) -> int | None:
    """Calculate days until a target date."""
    if not target_date:
        return None
    now = datetime.now(timezone.utc)
    delta = target_date - now
    return delta.days


# =============================================================================
# CHECK FUNCTION
# =============================================================================

# Status mapping
STATUS_STATE_MAP = {
    "Valid": State.OK,
    "Invalid": State.CRIT,
    "Expired": State.CRIT,
}


def check_veeam_rest_license(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check Veeam license status."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No license data received")
        return

    # Extract license properties
    status = section.get("status", "Unknown")
    license_type = section.get("type", "Unknown")
    edition = section.get("edition", "Unknown")
    licensed_to = section.get("licensedTo", "")
    support_id = section.get("supportId", "")
    expiration_date = section.get("expirationDate")
    support_expiration_date = section.get("supportExpirationDate")
    auto_update = section.get("autoUpdateEnabled", False)
    proactive_support = section.get("proactiveSupportEnabled", False)

    # License summaries
    instance_summary = section.get("instanceLicenseSummary", {})
    socket_summary = section.get("socketLicenseSummary", {})
    capacity_summary = section.get("capacityLicenseSummary", {})

    # Check license status
    state = STATUS_STATE_MAP.get(status, State.UNKNOWN)
    yield Result(state=state, summary=f"License status: {status}")

    # Check license expiration
    exp_date = _parse_datetime(expiration_date)
    if exp_date:
        days_left = _days_until(exp_date)
        if days_left is not None:
            exp_warn = params.get("license_expiration_warn", 30)
            exp_crit = params.get("license_expiration_crit", 7)

            threshold_info = f"(warn/crit below {exp_warn}/{exp_crit} days)"
            if days_left < 0:
                yield Result(
                    state=State.CRIT,
                    summary=f"License expired {abs(days_left)} days ago {threshold_info}",
                )
            elif days_left <= exp_crit:
                yield Result(
                    state=State.CRIT,
                    summary=f"License expires in {days_left} days {threshold_info}",
                )
            elif days_left <= exp_warn:
                yield Result(
                    state=State.WARN,
                    summary=f"License expires in {days_left} days {threshold_info}",
                )
            else:
                yield Result(
                    state=State.OK,
                    summary=f"License expires in {days_left} days {threshold_info}",
                )
            yield Metric("license_days_remaining", days_left)

    # Check support expiration
    support_exp_date = _parse_datetime(support_expiration_date)
    if support_exp_date:
        support_days_left = _days_until(support_exp_date)
        if support_days_left is not None:
            support_exp_warn = params.get("support_expiration_warn", 30)
            support_exp_crit = params.get("support_expiration_crit", 7)

            support_threshold_info = f"(warn/crit below {support_exp_warn}/{support_exp_crit} days)"
            if support_days_left < 0:
                yield Result(
                    state=State.WARN,
                    summary=f"Support contract expired {abs(support_days_left)} days ago {support_threshold_info}",
                )
            elif support_days_left <= support_exp_crit:
                yield Result(
                    state=State.WARN,
                    summary=f"Support contract expires in {support_days_left} days {support_threshold_info}",
                )
            elif support_days_left <= support_exp_warn:
                yield Result(
                    state=State.WARN,
                    summary=f"Support contract expires in {support_days_left} days {support_threshold_info}",
                )
            else:
                yield Result(
                    state=State.OK,
                    summary=f"Support contract expires in {support_days_left} days {support_threshold_info}",
                )
            yield Metric("support_days_remaining", support_days_left)

    # Check instance license usage
    if instance_summary:
        licensed = instance_summary.get("licensedInstancesNumber", 0)
        used = instance_summary.get("usedInstancesNumber", 0)

        if licensed > 0:
            usage_percent = (used / licensed) * 100
            usage_warn = params.get("instance_usage_warn", 80.0)
            usage_crit = params.get("instance_usage_crit", 95.0)

            usage_threshold_info = f"(warn/crit at {usage_warn:.0f}/{usage_crit:.0f}%)"
            if usage_percent >= usage_crit:
                yield Result(
                    state=State.CRIT,
                    summary=f"Instance usage: {used:.0f}/{licensed:.0f} ({usage_percent:.1f}%) {usage_threshold_info}",
                )
            elif usage_percent >= usage_warn:
                yield Result(
                    state=State.WARN,
                    summary=f"Instance usage: {used:.0f}/{licensed:.0f} ({usage_percent:.1f}%) {usage_threshold_info}",
                )
            else:
                yield Result(
                    state=State.OK,
                    summary=f"Instance usage: {used:.0f}/{licensed:.0f} ({usage_percent:.1f}%) {usage_threshold_info}",
                )

            yield Metric("license_instances_used", used)
            yield Metric("license_instances_licensed", licensed)
            yield Metric("license_instances_usage_percent", usage_percent, boundaries=(0, 100))

    # Check socket license usage
    if socket_summary:
        licensed_sockets = socket_summary.get("licensedSocketsNumber", 0)
        used_sockets = socket_summary.get("usedSocketsNumber", 0)

        if licensed_sockets > 0:
            socket_usage_percent = (used_sockets / licensed_sockets) * 100
            yield Result(
                state=State.OK,
                notice=f"Socket usage: {used_sockets}/{licensed_sockets}",
            )
            yield Metric("license_sockets_used", used_sockets)
            yield Metric("license_sockets_licensed", licensed_sockets)

    # Check capacity license usage
    if capacity_summary:
        licensed_capacity_tb = capacity_summary.get("licensedCapacityTb", 0)
        used_capacity_tb = capacity_summary.get("usedCapacityTb", 0)

        if licensed_capacity_tb > 0:
            capacity_usage_percent = (used_capacity_tb / licensed_capacity_tb) * 100
            yield Result(
                state=State.OK,
                notice=f"Capacity usage: {used_capacity_tb:.1f}/{licensed_capacity_tb:.1f} TB",
            )
            yield Metric("license_capacity_used_tb", used_capacity_tb)
            yield Metric("license_capacity_licensed_tb", licensed_capacity_tb)

    # Details
    details_parts = [
        f"Edition: {edition}",
        f"Type: {license_type}",
    ]
    if licensed_to:
        details_parts.append(f"Licensed to: {licensed_to}")
    if support_id:
        details_parts.append(f"Support ID: {support_id}")
    if auto_update:
        details_parts.append("Auto-update: enabled")
    if proactive_support:
        details_parts.append("Proactive support: enabled")

    yield Result(state=State.OK, notice=", ".join(details_parts))


check_plugin_veeam_rest_license = CheckPlugin(
    name="veeam_rest_license",
    service_name="Veeam License",
    discovery_function=discover_veeam_rest_license,
    check_function=check_veeam_rest_license,
    check_default_parameters={
        "license_expiration_warn": 30,  # days
        "license_expiration_crit": 7,   # days
        "support_expiration_warn": 30,  # days
        "support_expiration_crit": 7,   # days
        "instance_usage_warn": 80.0,    # percent
        "instance_usage_crit": 95.0,    # percent
    },
    check_ruleset_name="veeam_rest_license",
)
