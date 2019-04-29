from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import AnyStr, Type

from os_credits.influx.model import InfluxDBPoint
from os_credits.log import internal_logger

from .base_models import (
    REGISTERED_MEASUREMENTS,
    Metric,
    TotalUsageMetric,
    UsageMeasurement,
)


class VCPUMetric(
    TotalUsageMetric, measurement_name="project_vcpu_usage", friendly_name="cpu"
):

    CREDITS_PER_VIRTUAL_HOUR = Decimal(1)
    property_description = "Amount of vCPUs."


class RAMMetric(
    TotalUsageMetric, measurement_name="project_mb_usage", friendly_name="ram"
):

    # always specify the amount as string to prevent inaccuracies of builtin float
    CREDITS_PER_VIRTUAL_HOUR = Decimal("0.03")
    property_description = "Amount of RAM in MB."


# located next to the metrics to ensure that their classes are initialized and therefore
# registered in REGISTERED_MEASUREMENTS
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
    metric: Type[Metric] = VCPUMetric


@dataclass(frozen=True)
class _RAMMeasurement(UsageMeasurement):
    metric: Type[Metric] = RAMMetric


@dataclass(frozen=True)
class BillingHistory(InfluxDBPoint):

    credits_left: Decimal = field(metadata={"component": "field", "decoder": Decimal})
    metric_name: str = field(metadata={"component": "tag"})
    metric_friendly_name: str = field(metadata={"component": "tag"})

    def __post_init__(self) -> None:
        internal_logger.debug("Constructed billing history point %s", self)
