from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Optional, Type, TypeVar

from os_credits.exceptions import MeasurementError
from os_credits.influx.model import InfluxDBPoint

REGISTERED_MEASUREMENTS = {}

# MeasurementType
MT = TypeVar("MT", bound="UsageMeasurement")


class Metric:
    _metrics: Dict[str, Type[Metric]] = {}

    CREDITS_PER_VIRTUAL_HOUR: Optional[float] = None
    property_description = ""

    measurement_name: str
    friendly_name: str

    def __init_subclass__(cls, measurement_name: str, friendly_name: str) -> None:
        Metric._metrics.update({measurement_name: cls})
        cls.measurement_name = measurement_name
        cls.friendly_name = friendly_name

    @classmethod
    def calculate_credits(
        cls, *, current_measurement: MT, older_measurement: MT
    ) -> float:
        """
        Base implementation how to bill two measurements of the same type. Expected to
        be overwritten by subclasses whose billing logic goes beyond subtracting usage
        values, e.g. if your current_measurement values are not continuously increasing
        but fluctuating, i.e. being a delta instead of a total sum.
        """
        if current_measurement.metric is not older_measurement.metric:
            raise TypeError("Measurements must be of same type")
        if cls.CREDITS_PER_VIRTUAL_HOUR is None or cls.CREDITS_PER_VIRTUAL_HOUR <= 0:
            raise ValueError(
                f"UsageMeasurement type {type(cls)} does neither define a positive "
                "`CREDITS_PER_VIRTUAL_HOUR` nor overwrites `calculate_credits`"
            )
        if current_measurement.time < older_measurement.time:
            raise MeasurementError(
                "Passed current_measurement must be older. Use the top-level "
                "`calculate_credits` function to prevent this error."
            )
        return (
            float(current_measurement.value - older_measurement.value)
            * cls.CREDITS_PER_VIRTUAL_HOUR
        )

    @classmethod
    def from_measurement(cls, name: str) -> Type[Metric]:
        try:
            return cls._metrics[name]
        except KeyError:
            raise ValueError(f"UsageMeasurement `{name}` it not supported/needed.")

    @classmethod
    def is_supported(cls, measurement_name: str) -> bool:
        return measurement_name in cls._metrics

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
            "description": cls.property_description,
            "measurement_name": cls.measurement_name,
        }

    @classmethod
    @lru_cache()
    def friendly_name_to_usage(cls) -> Dict[str, Type[Metric]]:
        return {m.friendly_name: m for m in Metric._metrics.values()}

    @classmethod
    def costs_per_hour(cls, spec: int) -> float:
        """
        Simple base implementation according to _calculate_credits. Expected to be
        overwritten in more complex measurement classes.
        """
        if cls.CREDITS_PER_VIRTUAL_HOUR is None or cls.CREDITS_PER_VIRTUAL_HOUR <= 0:
            raise ValueError(
                f"Metric type {cls.__name__} does neither define a positive "
                "`CREDITS_PER_VIRTUAL_HOUR` nor overwrites `calculate_credits`"
            )
        return spec * cls.CREDITS_PER_VIRTUAL_HOUR


@dataclass(init=False, frozen=True)
class UsageMeasurement(InfluxDBPoint):
    location_id: int = field(metadata={"component": "tag", "decoder": int})
    project_name: str = field(metadata={"component": "tag"})
    value: float = field(metadata={"component": "field", "decoder": float})
    metric: Type[Metric] = field(
        repr=False, init=False, compare=False, metadata={"component": None}
    )

    def __init_subclass__(cls: Type[UsageMeasurement]) -> None:
        REGISTERED_MEASUREMENTS[cls.metric.measurement_name] = cls