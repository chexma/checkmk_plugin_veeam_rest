#!/usr/bin/env python3
"""
Check plugin for Veeam Configuration Backup.

Monitors configuration backup status - critical for disaster recovery.
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


def parse_veeam_rest_config_backup(string_table: StringTable) -> Section | None:
    """Parse JSON output from special agent."""
    if not string_table:
        return None

    try:
        json_str = "".join(line[0] for line in string_table)
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None


agent_section_veeam_rest_config_backup = AgentSection(
    name="veeam_rest_config_backup",
    parse_function=parse_veeam_rest_config_backup,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_config_backup(section: Section) -> DiscoveryResult:
    """Discover Veeam configuration backup."""
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


def _calculate_age_seconds(target_date: datetime | None) -> int | None:
    """Calculate seconds since a target date."""
    if not target_date:
        return None
    now = datetime.now(timezone.utc)
    delta = now - target_date
    return int(delta.total_seconds())


# =============================================================================
# CHECK FUNCTION
# =============================================================================

def check_veeam_rest_config_backup(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check Veeam configuration backup status."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # Extract configuration backup properties
    is_enabled = section.get("isEnabled", False)
    restore_points_to_keep = section.get("restorePointsToKeep", 0)

    # Get encryption info
    encryption = section.get("encryption", {})
    encryption_enabled = encryption.get("isEnabled", False)

    # Get last successful backup info
    last_backup = section.get("lastSuccessfulBackup", {})
    last_backup_time_str = last_backup.get("lastSuccessfulTime")
    last_backup_time = _parse_datetime(last_backup_time_str)

    # Check if configuration backup is enabled
    if not is_enabled:
        yield Result(
            state=State.CRIT,
            summary="Configuration backup is DISABLED",
        )
        yield Result(
            state=State.OK,
            notice="Enable configuration backup for disaster recovery",
        )
        return

    # Configuration backup is enabled
    state = State.OK
    summary_parts = ["Configuration backup enabled"]

    # Check backup age
    if last_backup_time:
        age_seconds = _calculate_age_seconds(last_backup_time)
        if age_seconds is not None:
            # Get thresholds from params (default: 7 days warn, 14 days crit)
            age_warn_days = params.get("backup_age_warn", 7)
            age_crit_days = params.get("backup_age_crit", 14)

            # Convert days to seconds
            age_warn_seconds = age_warn_days * 86400
            age_crit_seconds = age_crit_days * 86400

            # Check levels
            yield from check_levels(
                age_seconds,
                levels_upper=("fixed", (age_warn_seconds, age_crit_seconds)),
                metric_name="veeam_rest_config_backup_age",
                render_func=render.timespan,
                label="Last backup",
            )

            # Add age to summary
            age_days = age_seconds // 86400
            if age_days == 0:
                summary_parts.append("last backup today")
            elif age_days == 1:
                summary_parts.append("last backup 1 day ago")
            else:
                summary_parts.append(f"last backup {age_days} days ago")
    else:
        yield Result(
            state=State.WARN,
            summary="No successful backup recorded",
        )
        return

    # Build summary
    yield Result(state=state, summary=", ".join(summary_parts))

    # Details
    yield Result(
        state=State.OK,
        notice=f"Encryption: {'enabled' if encryption_enabled else 'disabled'}",
    )
    yield Result(
        state=State.OK,
        notice=f"Restore points to keep: {restore_points_to_keep}",
    )

    if last_backup_time_str:
        yield Result(
            state=State.OK,
            notice=f"Last successful backup: {last_backup_time_str}",
        )

    # Repository info
    backup_repo_id = section.get("backupRepositoryId")
    if backup_repo_id:
        yield Result(
            state=State.OK,
            notice=f"Repository ID: {backup_repo_id}",
        )


check_plugin_veeam_rest_config_backup = CheckPlugin(
    name="veeam_rest_config_backup",
    service_name="Veeam Config Backup",
    discovery_function=discover_veeam_rest_config_backup,
    check_function=check_veeam_rest_config_backup,
    check_default_parameters={
        "backup_age_warn": 7,   # 7 days
        "backup_age_crit": 14,  # 14 days
    },
    check_ruleset_name="veeam_rest_config_backup",
)
