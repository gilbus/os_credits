from __future__ import annotations

from dataclasses import dataclass, field
from typing import AnyStr, Type

from os_credits.influx.model import InfluxDBPoint

from .base_models import REGISTERED_MEASUREMENTS, Metric, UsageMeasurement


class _VCPUMetric(Metric, measurement_name="project_vcpu_usage", friendly_name="cpu"):

    CREDITS_PER_VIRTUAL_HOUR = 1
    property_description = "Amount of vCPUs."


class _RAMMetric(Metric, measurement_name="project_mb_usage", friendly_name="ram"):

    CREDITS_PER_VIRTUAL_HOUR = 0.3
    property_description = "Amount of RAM in MB."


def measurement_by_name(name: AnyStr) -> Type[UsageMeasurement]:
    """
    :param name: The name of the measurement or a text in InfluxDB Line Protocol from
    which the name is extracted.
    """
    if isinstance(name, bytes):
        influx_line = name.decode()
    else:
        influx_line = name

    measurement_name = influx_line.split(",", 1)[0]
    try:
        return REGISTERED_MEASUREMENTS[measurement_name]
    except KeyError:
        raise ValueError(f"Measurement `{name}` it not supported/needed.")


@dataclass(frozen=True)
class _VCPUMeasurement(UsageMeasurement):
    metric: Type[Metric] = _VCPUMetric


@dataclass(frozen=True)
class _RAMMeasurement(UsageMeasurement):
    metric: Type[Metric] = _RAMMetric


@dataclass(frozen=True)
class BillingHistory(InfluxDBPoint):

    credits: float = field(metadata={"component": "field", "decoder": float})
    metric_name: str = field(metadata={"component": "tag"})
    metric_friendly_name: str = field(metadata={"component": "tag"})
