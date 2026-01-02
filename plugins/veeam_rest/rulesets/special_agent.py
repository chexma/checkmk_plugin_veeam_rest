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
            "hostname": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Veeam Server Hostname"),
                    help_text=Help(
                        "Hostname or IP address of the Veeam B&R server. "
                        "If not specified, the host address is used."
                    ),
                ),
            ),
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
                    title=Title("Maximum Session/Task Age"),
                    help_text=Help(
                        "Only fetch sessions and task details younger than this. "
                        "Reducing this value improves performance."
                    ),
                    displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.DAY],
                    prefill=DefaultValue(86400),  # 24 hours
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
