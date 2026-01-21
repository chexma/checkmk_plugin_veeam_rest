#!/usr/bin/env python3
"""
WATO ruleset for the Veeam REST API special agent.

This defines the configuration form in Setup > Agents > Other integrations.
"""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    migrate_to_password,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Backup & Replication (REST API)"),
        help_text=Help(
            "This rule configures the special agent for monitoring "
            "Veeam Backup & Replication servers via REST API. "
            "Requires Veeam B&R 12.0 or later with REST API enabled on port 9419."
        ),
        elements={
            # Connection settings
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("REST API Port"),
                    help_text=Help("Default is 9419"),
                    prefill=DefaultValue(9419),
                    custom_validate=(validators.NumberInRange(min_value=1, max_value=65535),),
                ),
            ),
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help(
                        "Veeam admin username. Format: DOMAIN\\user or user@domain.com"
                    ),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help("Password for the Veeam admin user"),
                    migrate=migrate_to_password,
                ),
            ),
            "no_cert_check": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Disable SSL Certificate Verification"),
                    label=Title("Do not verify SSL certificate"),
                    help_text=Help(
                        "Use this for self-signed certificates. "
                        "Not recommended for production environments."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connection Timeout"),
                    help_text=Help("Timeout in seconds for API requests"),
                    prefill=DefaultValue(60),
                    custom_validate=(validators.NumberInRange(min_value=5, max_value=300),),
                ),
            ),
            # Data collection options
            "sections": DictElement(
                required=False,
                parameter_form=MultipleChoice(
                    title=Title("Sections to Collect"),
                    help_text=Help(
                        "Select which data sections to retrieve from Veeam. "
                        "More sections mean more API calls and longer check times."
                    ),
                    elements=[
                        MultipleChoiceElement(
                            name="jobs",
                            title=Title("Backup Jobs"),
                        ),
                        MultipleChoiceElement(
                            name="repositories",
                            title=Title("Repositories"),
                        ),
                        MultipleChoiceElement(
                            name="proxies",
                            title=Title("Proxies"),
                        ),
                        MultipleChoiceElement(
                            name="managed_servers",
                            title=Title("Managed Servers"),
                        ),
                        MultipleChoiceElement(
                            name="license",
                            title=Title("License Information"),
                        ),
                        MultipleChoiceElement(
                            name="server",
                            title=Title("Backup Server Information"),
                        ),
                        MultipleChoiceElement(
                            name="scaleout_repositories",
                            title=Title("Scale-Out Repositories"),
                        ),
                        MultipleChoiceElement(
                            name="wan_accelerators",
                            title=Title("WAN Accelerators"),
                        ),
                        MultipleChoiceElement(
                            name="malware_events",
                            title=Title("Malware Detection Events"),
                        ),
                    ],
                    prefill=DefaultValue(["jobs", "repositories", "proxies"]),
                ),
            ),
            # Service output options
            "backup_mode": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Backup Services"),
                    help_text=Help(
                        "Configure how backup object services are created. "
                        "Piggyback attaches services to target VMs/hosts, Server creates services "
                        "directly on the Veeam server."
                    ),
                    elements=[
                        SingleChoiceElement(name="disabled", title=Title("Disabled")),
                        SingleChoiceElement(
                            name="piggyback_vms",
                            title=Title("Attach to Hosts"),
                        ),
                        SingleChoiceElement(
                            name="backup_server",
                            title=Title("Attach to Backup Server"),
                        ),
                    ],
                    prefill=DefaultValue("disabled"),
                ),
            ),
            "malware_mode": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Malware Services"),
                    help_text=Help(
                        "Configure how malware event services are created. "
                        "Requires 'Malware Detection Events' in Sections to Collect."
                    ),
                    elements=[
                        SingleChoiceElement(name="disabled", title=Title("Disabled")),
                        SingleChoiceElement(
                            name="piggyback_hosts",
                            title=Title("Attach to Hosts"),
                        ),
                        SingleChoiceElement(
                            name="backup_server",
                            title=Title("Attach to Backup Server"),
                        ),
                    ],
                    prefill=DefaultValue("disabled"),
                ),
            ),
            # Filtering options
            "session_age": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    title=Title("Maximum Session/Task Age"),
                    help_text=Help(
                        "Only fetch sessions and task details younger than this. "
                        "Reducing this value improves performance."
                    ),
                    displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.DAY],
                    prefill=DefaultValue(86400),  # 24 hours
                ),
            ),
            "restore_points_days": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Restore Points Age (Days)"),
                    help_text=Help(
                        "Only fetch restore points from the last N days. "
                        "This dramatically improves performance in large environments. "
                        "Default: 7 days. Set to 0 to fetch all (not recommended)."
                    ),
                    prefill=DefaultValue(7),
                    custom_validate=(validators.NumberInRange(min_value=0, max_value=365),),
                ),
            ),
            # Caching options
            "no_cache": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Disable Caching"),
                    label=Title("Disable all section caching"),
                    help_text=Help(
                        "By default, sections are cached to reduce API load. "
                        "Enable this to always fetch fresh data."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
            "cache_intervals": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Cache Intervals per Section"),
                    help_text=Help(
                        "Override default cache intervals for specific sections. "
                        "Set to 0 to disable caching for a section. "
                        "Leave empty to use defaults."
                    ),
                    elements={
                        "jobs": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("Jobs"),
                                help_text=Help("Default: 5 minutes"),
                                displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.HOUR],
                                prefill=DefaultValue(300),
                            ),
                        ),
                        "repositories": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("Repositories"),
                                help_text=Help("Default: 30 minutes"),
                                displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.HOUR],
                                prefill=DefaultValue(1800),
                            ),
                        ),
                        "proxies": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("Proxies"),
                                help_text=Help("Default: 1 hour"),
                                displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.HOUR],
                                prefill=DefaultValue(3600),
                            ),
                        ),
                        "managed_servers": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("Managed Servers"),
                                help_text=Help("Default: 1 hour"),
                                displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.HOUR],
                                prefill=DefaultValue(3600),
                            ),
                        ),
                        "license": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("License"),
                                help_text=Help("Default: 24 hours"),
                                displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.DAY],
                                prefill=DefaultValue(86400),
                            ),
                        ),
                        "server": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("Server Info"),
                                help_text=Help("Default: 24 hours"),
                                displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.DAY],
                                prefill=DefaultValue(86400),
                            ),
                        ),
                        "scaleout_repositories": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("Scale-Out Repositories"),
                                help_text=Help("Default: 30 minutes"),
                                displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.HOUR],
                                prefill=DefaultValue(1800),
                            ),
                        ),
                        "wan_accelerators": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("WAN Accelerators"),
                                help_text=Help("Default: 1 hour"),
                                displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.HOUR],
                                prefill=DefaultValue(3600),
                            ),
                        ),
                        "malware_events": DictElement(
                            required=False,
                            parameter_form=TimeSpan(
                                title=Title("Malware Events"),
                                help_text=Help("Default: 5 minutes"),
                                displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.HOUR],
                                prefill=DefaultValue(300),
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_veeam_rest = SpecialAgent(
    name="veeam_rest",
    title=Title("Veeam Backup & Replication (REST API)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
    help_text=Help(
        "Monitors Veeam Backup & Replication servers using the REST API. "
        "Collects backup job status, repository capacity, proxy status, and more."
    ),
)
