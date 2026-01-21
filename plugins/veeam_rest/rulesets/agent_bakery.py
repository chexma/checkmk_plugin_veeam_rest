#!/usr/bin/env python3
"""
WATO ruleset for deploying the Veeam REST API agent plugin via Agent Bakery.

This defines the configuration form in Setup > Agents > Windows, Linux, Solaris, AIX > Agent rules.
The plugin runs locally on the Veeam server, connecting to localhost - no firewall ports needed.
"""

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
    migrate_to_password,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam REST API Agent Plugin"),
        help_text=Help(
            "Deploy the Veeam REST API agent plugin to Windows hosts running "
            "Veeam Backup & Replication. The plugin connects to the local REST API "
            "(localhost:9419), so no firewall ports need to be opened to the CheckMK server. "
            "This is an alternative to the special agent approach."
        ),
        elements={
            # Authentication
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
            # Connection settings
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("REST API Port"),
                    help_text=Help("Default is 9419. The plugin always connects to localhost."),
                    prefill=DefaultValue(9419),
                    custom_validate=(validators.NumberInRange(min_value=1, max_value=65535),),
                ),
            ),
            "no_cert_check": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Disable SSL Certificate Verification"),
                    label=Label("Do not verify SSL certificate"),
                    help_text=Help(
                        "Recommended for localhost connections with self-signed certificates."
                    ),
                    prefill=DefaultValue(True),
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
                            name="tasks",
                            title=Title("Task Sessions (per-VM details)"),
                        ),
                        MultipleChoiceElement(
                            name="sessions",
                            title=Title("Sessions"),
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
                    ],
                    prefill=DefaultValue(["jobs", "tasks", "repositories", "proxies"]),
                ),
            ),
            # Filtering options
            "session_age": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    title=Title("Maximum Task/Malware Event Age"),
                    help_text=Help(
                        "Only fetch task sessions (for backup metrics) and malware events "
                        "younger than this. Reducing this value improves performance."
                    ),
                    displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.DAY],
                    prefill=DefaultValue(86400.0),  # 24 hours
                ),
            ),
            # Caching/async execution
            "cache_interval": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    title=Title("Cache Interval"),
                    help_text=Help(
                        "How long to cache the plugin output. The plugin will run asynchronously "
                        "and results will be cached for this duration. Set to 0 for synchronous execution."
                    ),
                    displayed_magnitudes=[TimeMagnitude.SECOND, TimeMagnitude.MINUTE],
                    prefill=DefaultValue(300.0),  # 5 minutes
                ),
            ),
        },
    )


rule_spec_agent_config_veeam_rest = AgentConfig(
    name="veeam_rest",
    title=Title("Veeam REST API Agent Plugin"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
    help_text=Help(
        "Deploy the Veeam REST API agent plugin to monitor Veeam Backup & Replication "
        "servers locally. The plugin runs on the Veeam server itself and connects to "
        "localhost, avoiding the need to open firewall ports for remote access."
    ),
)
