#!/usr/bin/env python3
"""
Graphing definitions for Veeam REST monitoring.

Defines metrics, graphs, and perfometers for visualization.
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Open, Perfometer


# =============================================================================
# UNITS
# =============================================================================

UNIT_BYTES = Unit(IECNotation("B"))
UNIT_PERCENTAGE = Unit(DecimalNotation("%"), StrictPrecision(1))
UNIT_TIME = Unit(TimeNotation())


# =============================================================================
# REPOSITORY METRICS
# =============================================================================

metric_repository_capacity = Metric(
    name="repository_capacity",
    title=Title("Repository capacity"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_repository_used = Metric(
    name="repository_used",
    title=Title("Repository used space"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

metric_repository_free = Metric(
    name="repository_free",
    title=Title("Repository free space"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

metric_repository_used_percent = Metric(
    name="repository_used_percent",
    title=Title("Repository usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)


# =============================================================================
# TASK/BACKUP METRICS
# =============================================================================

metric_backup_age = Metric(
    name="backup_age",
    title=Title("Backup age"),
    unit=UNIT_TIME,
    color=Color.PURPLE,
)

metric_backup_duration = Metric(
    name="backup_duration",
    title=Title("Backup duration"),
    unit=UNIT_TIME,
    color=Color.BLUE,
)

metric_backup_size_processed = Metric(
    name="backup_size_processed",
    title=Title("Processed data"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

metric_backup_size_read = Metric(
    name="backup_size_read",
    title=Title("Read data"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

metric_backup_size_transferred = Metric(
    name="backup_size_transferred",
    title=Title("Transferred data"),
    unit=UNIT_BYTES,
    color=Color.ORANGE,
)


# =============================================================================
# GRAPHS
# =============================================================================

graph_repository_usage = Graph(
    name="veeam_repository_usage",
    title=Title("Veeam Repository Usage"),
    compound_lines=["repository_used"],
    simple_lines=["repository_capacity"],
    minimal_range=MinimalRange(0, 1),
)

graph_repository_space = Graph(
    name="veeam_repository_space",
    title=Title("Veeam Repository Space"),
    compound_lines=["repository_used", "repository_free"],
    minimal_range=MinimalRange(0, 1),
)

graph_backup_data = Graph(
    name="veeam_backup_data",
    title=Title("Veeam Backup Data Transfer"),
    simple_lines=[
        "backup_size_processed",
        "backup_size_read",
        "backup_size_transferred",
    ],
    minimal_range=MinimalRange(0, 1),
)

graph_backup_timing = Graph(
    name="veeam_backup_timing",
    title=Title("Veeam Backup Timing"),
    simple_lines=["backup_duration", "backup_age"],
    minimal_range=MinimalRange(0, 1),
)


# =============================================================================
# PERFOMETERS
# =============================================================================

perfometer_repository_usage = Perfometer(
    name="veeam_repository_usage",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["repository_used_percent"],
)


# =============================================================================
# JOB METRICS
# =============================================================================

metric_job_duration = Metric(
    name="job_duration",
    title=Title("Job duration"),
    unit=UNIT_TIME,
    color=Color.BLUE,
)

metric_job_size_processed = Metric(
    name="job_size_processed",
    title=Title("Job processed data"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

metric_job_size_read = Metric(
    name="job_size_read",
    title=Title("Job read data"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

metric_job_size_transferred = Metric(
    name="job_size_transferred",
    title=Title("Job transferred data"),
    unit=UNIT_BYTES,
    color=Color.ORANGE,
)


# =============================================================================
# JOB GRAPHS
# =============================================================================

graph_job_duration = Graph(
    name="veeam_job_duration",
    title=Title("Veeam Job Duration"),
    simple_lines=["job_duration"],
    minimal_range=MinimalRange(0, 1),
)

graph_job_data = Graph(
    name="veeam_job_data",
    title=Title("Veeam Job Data Transfer"),
    simple_lines=[
        "job_size_processed",
        "job_size_read",
        "job_size_transferred",
    ],
    minimal_range=MinimalRange(0, 1),
)


# =============================================================================
# LICENSE METRICS
# =============================================================================

UNIT_DAYS = Unit(DecimalNotation(" days"))
UNIT_COUNT = Unit(DecimalNotation(""))

metric_license_days_remaining = Metric(
    name="license_days_remaining",
    title=Title("License days remaining"),
    unit=UNIT_DAYS,
    color=Color.GREEN,
)

metric_support_days_remaining = Metric(
    name="support_days_remaining",
    title=Title("Support days remaining"),
    unit=UNIT_DAYS,
    color=Color.BLUE,
)

metric_license_instances_used = Metric(
    name="license_instances_used",
    title=Title("Instances used"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_license_instances_licensed = Metric(
    name="license_instances_licensed",
    title=Title("Instances licensed"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_license_instances_usage_percent = Metric(
    name="license_instances_usage_percent",
    title=Title("Instance usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.PURPLE,
)

metric_license_sockets_used = Metric(
    name="license_sockets_used",
    title=Title("Sockets used"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_license_sockets_licensed = Metric(
    name="license_sockets_licensed",
    title=Title("Sockets licensed"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_license_capacity_used_tb = Metric(
    name="license_capacity_used_tb",
    title=Title("Capacity used (TB)"),
    unit=Unit(DecimalNotation(" TB")),
    color=Color.ORANGE,
)

metric_license_capacity_licensed_tb = Metric(
    name="license_capacity_licensed_tb",
    title=Title("Capacity licensed (TB)"),
    unit=Unit(DecimalNotation(" TB")),
    color=Color.BLUE,
)


# =============================================================================
# WAN ACCELERATOR METRICS
# =============================================================================

metric_wan_accelerator_cache_size = Metric(
    name="wan_accelerator_cache_size",
    title=Title("WAN accelerator cache size"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_wan_accelerator_streams = Metric(
    name="wan_accelerator_streams",
    title=Title("WAN accelerator streams"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)


# =============================================================================
# LICENSE GRAPHS
# =============================================================================

graph_license_expiration = Graph(
    name="veeam_license_expiration",
    title=Title("Veeam License Expiration"),
    simple_lines=["license_days_remaining", "support_days_remaining"],
    minimal_range=MinimalRange(0, 1),
)

graph_license_instance_usage = Graph(
    name="veeam_license_instance_usage",
    title=Title("Veeam License Instance Usage"),
    simple_lines=["license_instances_used", "license_instances_licensed"],
    minimal_range=MinimalRange(0, 1),
)


# =============================================================================
# LICENSE PERFOMETERS
# =============================================================================

perfometer_license_instance_usage = Perfometer(
    name="veeam_license_instance_usage",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["license_instances_usage_percent"],
)
