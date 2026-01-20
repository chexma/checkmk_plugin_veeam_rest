#!/usr/bin/env python3
"""
WATO rulesets for Veeam REST check parameters.

These define the configurable thresholds for the check plugins.
"""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    IECMagnitude,
    Integer,
    LevelDirection,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, HostCondition, Topic


# =============================================================================
# VEEAM JOBS
# =============================================================================

def _state_choice() -> SingleChoice:
    """Create a single choice for OK/WARN/CRIT state selection."""
    return SingleChoice(
        elements=[
            SingleChoiceElement(name="ok", title=Title("OK")),
            SingleChoiceElement(name="warn", title=Title("WARNING")),
            SingleChoiceElement(name="crit", title=Title("CRITICAL")),
        ],
        prefill=DefaultValue("ok"),
    )


def _veeam_rest_jobs_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Backup Job Parameters"),
        elements={
            "max_job_age": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Maximum age of last job run"),
                    help_text=Help(
                        "Alert if the last successful job run is older than this threshold. "
                        "Value in hours."
                    ),
                    unit_symbol="hours",
                    prefill=DefaultValue(48),
                ),
            ),
            "ignore_disabled": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Ignore disabled jobs"),
                    help_text=Help(
                        "Do not alert on disabled jobs. By default, disabled jobs "
                        "generate a WARNING."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
            "result_states": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Job Result State Mapping"),
                    help_text=Help(
                        "Configure the monitoring state for each possible job result."
                    ),
                    elements={
                        "Success": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Success"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                        ),
                        "Warning": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Warning"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("warn"),
                            ),
                        ),
                        "Failed": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Failed"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("crit"),
                            ),
                        ),
                        "no_result": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("None (no run yet)"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                        ),
                    },
                ),
            ),
            "status_states": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Job Status State Mapping"),
                    help_text=Help(
                        "Configure the monitoring state for each possible job status. "
                        "Note: These are evaluated in addition to the result states."
                    ),
                    elements={
                        "Running": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Running"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                        ),
                        "Stopped": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Stopped"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                        ),
                        "Disabled": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Disabled"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("warn"),
                            ),
                        ),
                        "Inactive": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Inactive"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                        ),
                        "Enabled": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Enabled"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                        ),
                        "Starting": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Starting"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                        ),
                        "Stopping": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("Stopping"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warn", title=Title("WARNING")),
                                    SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_veeam_rest_jobs = CheckParameters(
    name="veeam_rest_jobs",
    title=Title("Veeam Backup Jobs"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_jobs_form,
    condition=HostAndItemCondition(item_title=Title("Job name")),
)


# =============================================================================
# VEEAM TASKS
# =============================================================================

def _veeam_rest_tasks_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Backup Task Parameters"),
        elements={
            "max_backup_age": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Maximum backup age"),
                    help_text=Help(
                        "Alert if the last backup of this object is older than this threshold. "
                        "Value in hours."
                    ),
                    unit_symbol="hours",
                    prefill=DefaultValue(48),
                ),
            ),
            "max_duration": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Maximum backup duration"),
                    help_text=Help(
                        "Alert if the backup took longer than this threshold. "
                        "Value in hours."
                    ),
                    unit_symbol="hours",
                    prefill=DefaultValue(8),
                ),
            ),
        },
    )


rule_spec_veeam_rest_tasks = CheckParameters(
    name="veeam_rest_tasks",
    title=Title("Veeam Backup Tasks"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_tasks_form,
    condition=HostAndItemCondition(item_title=Title("Object name")),
)


# =============================================================================
# VEEAM REPOSITORIES
# =============================================================================

def _veeam_rest_repositories_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Repository Parameters"),
        elements={
            "usage_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Repository usage levels"),
                    help_text=Help(
                        "Set warning and critical thresholds for repository usage percentage."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="%"),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                ),
            ),
            "free_space_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimum free space"),
                    help_text=Help(
                        "Set warning and critical thresholds for minimum free space."
                    ),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[IECMagnitude.GIBI],
                    ),
                    prefill_fixed_levels=DefaultValue((107374182400.0, 53687091200.0)),
                ),
            ),
        },
    )


rule_spec_veeam_rest_repositories = CheckParameters(
    name="veeam_rest_repositories",
    title=Title("Veeam Repositories"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_repositories_form,
    condition=HostAndItemCondition(item_title=Title("Repository name")),
)


# =============================================================================
# VEEAM PROXIES
# =============================================================================

def _veeam_rest_proxies_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Proxy Parameters"),
        help_text=Help("Currently no configurable parameters for proxy monitoring."),
        elements={},
    )


rule_spec_veeam_rest_proxies = CheckParameters(
    name="veeam_rest_proxies",
    title=Title("Veeam Proxies"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_proxies_form,
    condition=HostAndItemCondition(item_title=Title("Proxy name")),
)


# =============================================================================
# VEEAM LICENSE
# =============================================================================

def _veeam_rest_license_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam License Parameters"),
        elements={
            "license_expiration_warn": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("License expiration warning"),
                    help_text=Help(
                        "Alert with WARNING if the license expires within this many days."
                    ),
                    unit_symbol="days",
                    prefill=DefaultValue(30),
                ),
            ),
            "license_expiration_crit": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("License expiration critical"),
                    help_text=Help(
                        "Alert with CRITICAL if the license expires within this many days."
                    ),
                    unit_symbol="days",
                    prefill=DefaultValue(7),
                ),
            ),
            "support_expiration_warn": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Support expiration warning"),
                    help_text=Help(
                        "Alert with WARNING if the support contract expires within this many days."
                    ),
                    unit_symbol="days",
                    prefill=DefaultValue(30),
                ),
            ),
            "support_expiration_crit": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Support expiration critical"),
                    help_text=Help(
                        "Alert with WARNING if the support contract expires within this many days. "
                        "Note: Support expiration only generates WARNING, not CRITICAL."
                    ),
                    unit_symbol="days",
                    prefill=DefaultValue(7),
                ),
            ),
            "instance_usage_warn": DictElement(
                required=False,
                parameter_form=Float(
                    title=Title("Instance usage warning"),
                    help_text=Help(
                        "Alert with WARNING if instance license usage exceeds this percentage."
                    ),
                    unit_symbol="%",
                    prefill=DefaultValue(80.0),
                ),
            ),
            "instance_usage_crit": DictElement(
                required=False,
                parameter_form=Float(
                    title=Title("Instance usage critical"),
                    help_text=Help(
                        "Alert with CRITICAL if instance license usage exceeds this percentage."
                    ),
                    unit_symbol="%",
                    prefill=DefaultValue(95.0),
                ),
            ),
        },
    )


rule_spec_veeam_rest_license = CheckParameters(
    name="veeam_rest_license",
    title=Title("Veeam License"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_license_form,
    condition=HostCondition(),  # Singleton service - no item
)


# =============================================================================
# VEEAM SERVER
# =============================================================================

def _veeam_rest_server_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Server Parameters"),
        help_text=Help("Currently no configurable parameters for server monitoring."),
        elements={},
    )


rule_spec_veeam_rest_server = CheckParameters(
    name="veeam_rest_server",
    title=Title("Veeam Backup Server"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_server_form,
    condition=HostCondition(),  # Singleton service - no item
)


# =============================================================================
# VEEAM SCALE-OUT REPOSITORIES
# =============================================================================

def _veeam_rest_scaleout_repositories_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Scale-Out Repository Parameters"),
        help_text=Help("Currently no configurable parameters for scale-out repository monitoring."),
        elements={},
    )


rule_spec_veeam_rest_scaleout_repositories = CheckParameters(
    name="veeam_rest_scaleout_repositories",
    title=Title("Veeam Scale-Out Repositories"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_scaleout_repositories_form,
    condition=HostAndItemCondition(item_title=Title("Repository name")),
)


# =============================================================================
# VEEAM WAN ACCELERATORS
# =============================================================================

def _veeam_rest_wan_accelerators_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam WAN Accelerator Parameters"),
        help_text=Help("Currently no configurable parameters for WAN accelerator monitoring."),
        elements={},
    )


rule_spec_veeam_rest_wan_accelerators = CheckParameters(
    name="veeam_rest_wan_accelerators",
    title=Title("Veeam WAN Accelerators"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_wan_accelerators_form,
    condition=HostAndItemCondition(item_title=Title("Accelerator name")),
)


# =============================================================================
# SHARED ELEMENTS FOR VM/BACKUP OBJECT CHECKS
# =============================================================================

def _malware_status_elements() -> dict:
    """Shared malware status configuration elements for VM backup checks."""
    return {
        "malware_status_states": DictElement(
            required=False,
            parameter_form=Dictionary(
                title=Title("Malware Status State Mapping"),
                help_text=Help(
                    "Configure the monitoring state for each malware scan result. "
                    "By default, 'Suspicious' and 'NotScanned' generate warnings."
                ),
                elements={
                    "Clean": DictElement(
                        required=False,
                        parameter_form=SingleChoice(
                            title=Title("Clean"),
                            elements=[
                                SingleChoiceElement(name="ok", title=Title("OK")),
                                SingleChoiceElement(name="warn", title=Title("WARNING")),
                                SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                            ],
                            prefill=DefaultValue("ok"),
                        ),
                    ),
                    "Infected": DictElement(
                        required=False,
                        parameter_form=SingleChoice(
                            title=Title("Infected"),
                            elements=[
                                SingleChoiceElement(name="ok", title=Title("OK")),
                                SingleChoiceElement(name="warn", title=Title("WARNING")),
                                SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                            ],
                            prefill=DefaultValue("crit"),
                        ),
                    ),
                    "Suspicious": DictElement(
                        required=False,
                        parameter_form=SingleChoice(
                            title=Title("Suspicious"),
                            elements=[
                                SingleChoiceElement(name="ok", title=Title("OK")),
                                SingleChoiceElement(name="warn", title=Title("WARNING")),
                                SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                            ],
                            prefill=DefaultValue("warn"),
                        ),
                    ),
                    "NotScanned": DictElement(
                        required=False,
                        parameter_form=SingleChoice(
                            title=Title("Not Scanned"),
                            elements=[
                                SingleChoiceElement(name="ok", title=Title("OK")),
                                SingleChoiceElement(name="warn", title=Title("WARNING")),
                                SingleChoiceElement(name="crit", title=Title("CRITICAL")),
                            ],
                            prefill=DefaultValue("warn"),
                        ),
                    ),
                },
            ),
        ),
    }


# =============================================================================
# VEEAM VM BACKUP (PIGGYBACK)
# =============================================================================

def _veeam_rest_vm_backup_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam VM Backup Parameters"),
        elements={
            "backup_age_warn": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Backup age warning"),
                    help_text=Help("Alert with WARNING if backup is older than this (hours)."),
                    unit_symbol="hours",
                    prefill=DefaultValue(48),
                ),
            ),
            "backup_age_crit": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Backup age critical"),
                    help_text=Help("Alert with CRITICAL if backup is older than this (hours)."),
                    unit_symbol="hours",
                    prefill=DefaultValue(72),
                ),
            ),
            **_malware_status_elements(),
        },
    )


rule_spec_veeam_rest_vm_backup = CheckParameters(
    name="veeam_rest_vm_backup",
    title=Title("Veeam VM Backup (Piggyback)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_vm_backup_form,
    condition=HostCondition(),  # Singleton service on piggyback host
)


# =============================================================================
# VEEAM BACKUP OBJECTS (SERVER SERVICES)
# =============================================================================

def _veeam_rest_backup_objects_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Backup Object Parameters"),
        elements={
            "backup_age_warn": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Backup age warning"),
                    help_text=Help("Alert with WARNING if backup is older than this (hours)."),
                    unit_symbol="hours",
                    prefill=DefaultValue(48),
                ),
            ),
            "backup_age_crit": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Backup age critical"),
                    help_text=Help("Alert with CRITICAL if backup is older than this (hours)."),
                    unit_symbol="hours",
                    prefill=DefaultValue(72),
                ),
            ),
            **_malware_status_elements(),
        },
    )


rule_spec_veeam_rest_backup_objects = CheckParameters(
    name="veeam_rest_backup_objects",
    title=Title("Veeam Backup Objects (Server)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_veeam_rest_backup_objects_form,
    condition=HostAndItemCondition(item_title=Title("Object name")),
)
