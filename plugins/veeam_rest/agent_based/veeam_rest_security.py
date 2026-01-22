#!/usr/bin/env python3
"""
Check plugin for Veeam Security Analyzer / Best Practices.

Monitors security compliance and best practice violations.
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
)

from cmk_addons.plugins.veeam_rest.lib import parse_json_section


# =============================================================================
# SECTION PARSING
# =============================================================================

Section = list[dict[str, Any]]  # list of best practice checks


def parse_veeam_rest_security(string_table) -> Section | None:
    """Parse JSON list of best practice checks."""
    data = parse_json_section(string_table)
    if not data or not isinstance(data, list):
        return None
    return data if data else None


agent_section_veeam_rest_security = AgentSection(
    name="veeam_rest_security",
    parse_function=parse_veeam_rest_security,
)


# =============================================================================
# DISCOVERY
# =============================================================================

def discover_veeam_rest_security(section: Section) -> DiscoveryResult:
    """Discover Veeam security compliance service."""
    if section is not None:
        yield Service()


# =============================================================================
# CHECK FUNCTION
# =============================================================================

# Status mapping for best practice check status
STATUS_STATE_MAP = {
    "Passed": State.OK,
    "Failed": State.WARN,      # Failed checks are warnings by default
    "Suppressed": State.OK,     # Suppressed checks are OK (intentionally ignored)
    "NotApplicable": State.OK,  # Not applicable checks are OK
}


def check_veeam_rest_security(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """Check Veeam security compliance status."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent")
        return

    # Count checks by status
    passed = 0
    failed = 0
    suppressed = 0
    not_applicable = 0
    failed_checks: list[str] = []

    for check in section:
        status = check.get("status", "Unknown")
        name = check.get("name", "Unknown check")

        if status == "Passed":
            passed += 1
        elif status == "Failed":
            failed += 1
            failed_checks.append(name)
        elif status == "Suppressed":
            suppressed += 1
        elif status == "NotApplicable":
            not_applicable += 1

    total = passed + failed + suppressed + not_applicable

    # Metrics
    yield Metric("veeam_rest_security_passed", passed)
    yield Metric("veeam_rest_security_failed", failed)
    yield Metric("veeam_rest_security_suppressed", suppressed)
    yield Metric("veeam_rest_security_total", total)

    # Determine state based on failed checks
    # Get threshold from params (default: any failed check = WARN)
    warn_threshold = params.get("failed_warn", 1)
    crit_threshold = params.get("failed_crit", 5)

    if failed >= crit_threshold:
        state = State.CRIT
    elif failed >= warn_threshold:
        state = State.WARN
    else:
        state = State.OK

    # Build summary
    if failed == 0:
        summary = f"All {passed} security checks passed"
    else:
        summary = f"{failed} of {total} security checks failed"

    yield Result(state=state, summary=summary)

    # Show failed checks in details
    if failed_checks:
        yield Result(
            state=State.OK,
            notice=f"Failed checks: {', '.join(failed_checks[:10])}",  # Limit to first 10
        )
        if len(failed_checks) > 10:
            yield Result(
                state=State.OK,
                notice=f"... and {len(failed_checks) - 10} more",
            )

    # Statistics in details
    yield Result(state=State.OK, notice=f"Passed: {passed}")
    yield Result(state=State.OK, notice=f"Failed: {failed}")
    if suppressed > 0:
        yield Result(state=State.OK, notice=f"Suppressed: {suppressed}")
    if not_applicable > 0:
        yield Result(state=State.OK, notice=f"Not applicable: {not_applicable}")


check_plugin_veeam_rest_security = CheckPlugin(
    name="veeam_rest_security",
    service_name="Veeam Security Compliance",
    discovery_function=discover_veeam_rest_security,
    check_function=check_veeam_rest_security,
    check_default_parameters={
        "failed_warn": 1,   # Any failed check = WARN
        "failed_crit": 5,   # 5+ failed checks = CRIT
    },
    check_ruleset_name="veeam_rest_security",
)
