#!/usr/bin/env python3
"""
Server-side call configuration for the Veeam REST API special agent.

This module maps WATO ruleset parameters to command line arguments
for the special agent executable.
"""

from collections.abc import Iterator

from cmk.server_side_calls.v1 import (
    noop_parser,
    SpecialAgentConfig,
    SpecialAgentCommand,
    HostConfig,
)


def _agent_arguments(
    params: dict,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    """
    Convert GUI parameters to command line arguments.

    Args:
        params: Dictionary from ruleset configuration
        host_config: Host configuration object with:
            - host_config.name: Host name
            - host_config.primary_ip_config.address: IP address
            - host_config.alias: Host alias
    """
    args: list[str] = []

    # Connection settings - always use the Checkmk host's address
    args.extend(["--hostname", host_config.primary_ip_config.address])

    if "port" in params:
        args.extend(["--port", str(params["port"])])

    args.extend(["--username", params["username"]])

    # Password is a Password object, use unsafe() to get plain text
    args.extend(["--password", params["password"].unsafe()])

    # SSL verification
    if params.get("no_cert_check", False):
        args.append("--no-cert-check")

    # Timeout
    if "timeout" in params:
        args.extend(["--timeout", str(params["timeout"])])

    # Sections to collect
    sections = params.get("sections", ["jobs", "repositories", "proxies"])
    if sections:
        args.extend(["--sections"] + list(sections))

    # Backup service output mode
    backup_mode = params.get("backup_mode", "disabled")
    if backup_mode != "disabled":
        args.extend(["--backup-mode", backup_mode.replace("_", "-")])

    # Session age filter
    if "session_age" in params:
        args.extend(["--session-age", str(int(params["session_age"]))])

    # Restore points age filter (default: 7 days)
    restore_points_days = params.get("restore_points_days", 7)
    args.extend(["--restore-points-days", str(restore_points_days)])

    # Caching options
    if params.get("no_cache", False):
        args.append("--no-cache")
    elif "cache_intervals" in params:
        # Build comma-separated section:interval pairs
        cache_intervals = params["cache_intervals"]
        if cache_intervals:
            pairs = [f"{section}:{int(interval)}" for section, interval in cache_intervals.items()]
            if pairs:
                args.extend(["--cached-sections", ",".join(pairs)])

    yield SpecialAgentCommand(command_arguments=args)


special_agent_veeam_rest = SpecialAgentConfig(
    name="veeam_rest",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
