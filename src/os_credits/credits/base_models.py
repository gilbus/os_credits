from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from typing import Any, ClassVar, Dict, NewType, Type, TypeVar

from os_credits.exceptions import MeasurementError
from os_credits.influx.model import InfluxDBPoint
from os_credits.influx.valueTypes import InfluxValueType
from os_credits.log import internal_logger
from os_credits.settings import config

REGISTERED_MEASUREMENTS = {}

Credits = NewType("Credits", Decimal)
"""Distinct Credits type to prevent mixing of regular Decimals and Credits, since we
MUST apply quantize"""


class CreditsValueType(InfluxValueType[float], types=["Credits"]):
    @staticmethod
    def encode(value: Any) -> float:
        return float(value)

    @staticmethod
    def decode(value: Any) -> Credits:
        return Credits(Decimal(value).quantize(config["OS_CREDITS_PRECISION"]))


@dataclass(init=False, frozen=True)
class UsageMeasurement(InfluxDBPoint):
    location_id: int = field(metadata={"tag": True})
    project_name: str = field(metadata={"tag": True})
    value: float
    metric: Type[Metric] = field(
        repr=False, init=False, compare=False, metadata={"component": None}
    )

    def __init_subclass__(cls: Type[UsageMeasurement]) -> None:
        REGISTERED_MEASUREMENTS[cls.metric.name] = cls


# MeasurementType
MT = TypeVar("MT", bound=UsageMeasurement)


class Metric:
    _metrics: Dict[str, Type[Metric]] = {}

    description: ClassVar[str] = ""

    name: ClassVar[str]
    friendly_name: ClassVar[str]

    def __init_subclass__(cls, name: str, friendly_name: str) -> None:
        if None in (name, friendly_name):
            internal_logger.debug(
                "Not registering subclass %s of `Metric` since one or both of its names "
                "are None."
            )
            return
        Metric._metrics.update({name: cls})
        cls.name = name
        cls.friendly_name = friendly_name
        internal_logger.debug("Registered subclass of `Metric`: %s", cls)

    @classmethod
    def calculate_credits(
        cls, *, current_measurement: MT, older_measurement: MT
    ) -> Credits:
        raise NotImplementedError("Must be implemented by subclass.")

    @classmethod
    def api_information(cls) -> Dict[str, Any]:
        """
        Returns a dictionary containing the description and type information of this
        measurement.

        This is just a simple base implementation and should be overridden by subclasses
        if necessary.
        """
        return {
            "type": "int",
            "description": cls.description,
            "name": cls.name,
            "friendly_name": cls.friendly_name,
        }

    @classmethod
    @lru_cache()
    def friendly_name_to_usage(cls) -> Dict[str, Type[Metric]]:
        return {m.friendly_name: m for m in Metric._metrics.values()}

    @classmethod
    def costs_per_hour(cls, spec: int) -> Credits:
        raise NotImplementedError("Must be implemented by subclass.")


class TotalUsageMetric(
    Metric,
    # class definition must contain the following attributes to allow 'passthrough' from
    # child classes
    name=None,
    friendly_name=None,
):
    """Base class of every metric which is only billed by its usage values, i.e. the
    timestamps of any measurements are not considered at all.

    One example is the :class:`~os_credits.credits.models.VCPUMetric` which bills the
    amount of used virtual CPUs, the value of its corresponding measurement represents
    this time in hours.
    """

    CREDITS_PER_VIRTUAL_HOUR: ClassVar[Decimal]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if cls.CREDITS_PER_VIRTUAL_HOUR <= 0:
            raise ValueError(
                f"Metric type {cls.__name__} has non-positive "
                f"CREDITS_PER_VIRTUAL_HOUR({cls.CREDITS_PER_VIRTUAL_HOUR})."
            )
        super().__init_subclass__(**kwargs)

    @classmethod
    def costs_per_hour(cls, spec: int) -> Credits:
        """
        Simple base implementation according to _calculate_credits. Expected to be
        overwritten in more complex measurement classes.
        """
        return Credits(
            (spec * cls.CREDITS_PER_VIRTUAL_HOUR).quantize(
                config["OS_CREDITS_PRECISION"]
            )
        )

    @classmethod
    def calculate_credits(
        cls, *, current_measurement: MT, older_measurement: MT
    ) -> Credits:
        """
        Base implementation how to bill two measurements of the same type. Expected to
        be overwritten by subclasses whose billing logic goes beyond subtracting usage
        values, e.g. if your current_measurement values are not continuously increasing
        but fluctuating, i.e. being a delta instead of a total sum.
        """
        if current_measurement.metric is not older_measurement.metric:
            raise TypeError("Measurements must be of same type")
        if current_measurement.time < older_measurement.time:
            raise MeasurementError(
                "Passed current_measurement must be older. Use the top-level "
                "`calculate_credits` function to prevent this error."
            )
        return Credits(
            (
                Decimal(current_measurement.value - older_measurement.value)
                * cls.CREDITS_PER_VIRTUAL_HOUR
            ).quantize(config["OS_CREDITS_PRECISION"])
        )
