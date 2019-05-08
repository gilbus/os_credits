from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import AnyStr, Type

from os_credits.influx.model import InfluxDBPoint
from os_credits.log import internal_logger

from .base_models import (
    REGISTERED_MEASUREMENTS,
    Credits,
    Metric,
    TotalUsageMetric,
    UsageMeasurement,
)


class VCPUMetric(TotalUsageMetric, name="project_vcpu_usage", friendly_name="cpu"):

    CREDITS_PER_VIRTUAL_HOUR = Decimal(1)
    description = "Amount of vCPUs."


class RAMMetric(TotalUsageMetric, name="project_mb_usage", friendly_name="ram"):

    # always specify the amount as string to prevent inaccuracies of builtin float
    # division by 1024 to compensate for the usage of MiB instead of GiB
    CREDITS_PER_VIRTUAL_HOUR = Decimal("0.3") / Decimal(1024)
    description = (
        "Amount of RAM in MiB, meaning *1024 instead of *1000. Modeled this "
        "way since the same unit is used by OpenStack for its "
        "``os-simple-tenant-usage`` api."
    )


# located next to the metrics to ensure that their classes are initialized and therefore
# registered in REGISTERED_MEASUREMENTS
def measurement_by_name(name: AnyStr) -> Type[UsageMeasurement]:
    """Returns the correct :class:`UsageMeasurement` subclass corresponding to the given
    Influx Line.

    The measurement itself does not know its name, but its connected metric does.

    :param name: The name of the measurement or a text in InfluxDB Line Protocol from
        which the name is extracted.
    :return: Subclass of :class:`~os_credits.credits.base_models.UsageMeasurement`
        responsible for this measurement.
    :raises ValueError: No
        :class:`~os_credits.credits.base_models.UsageMeasurement`
        responsible/available, i.e. the passed measurement is not needed/supported.
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

    credits_left: Credits
    metric_name: str = field(metadata={"tag": True})
    metric_friendly_name: str = field(metadata={"tag": True})

    def __post_init__(self) -> None:
        internal_logger.debug("Constructed billing history point %s", self)
