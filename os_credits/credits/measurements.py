from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Optional, Type, TypeVar

from os_credits.exceptions import CalculationResultError, MeasurementError
from os_credits.influxdb import InfluxDBPoint


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
    def _calculate_credits(
        cls,
        *,
        current_measurement: UsageMeasurement,
        older_measurement: UsageMeasurement,
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
        if current_measurement.timestamp < older_measurement.timestamp:
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


class _DummyMetric(
    Metric, measurement_name="_dummy_placeholder", friendly_name="_dummy_placeholder"
):
    "Not thought for actual usage, only as default argument for UsageMeasurement"
    pass


class _VCPUUsage(Metric, measurement_name="project_vcpu_usage", friendly_name="cpu"):

    CREDITS_PER_VIRTUAL_HOUR = 1
    property_description = "Amount of vCPUs."


class _RAMUsage(Metric, measurement_name="project_mb_usage", friendly_name="ram"):

    CREDITS_PER_VIRTUAL_HOUR = 0.3
    property_description = "Amount of RAM in MB."


@dataclass
class UsageMeasurement(InfluxDBPoint):
    location_id: int = field(metadata={"component": "tag", "decoder": int})
    project_name: str = field(metadata={"component": "tag"})
    value: float = field(metadata={"component": "field", "decoder": float})
    metric: Type[Metric] = field(
        repr=False, init=False, compare=False, default=_DummyMetric
    )

    def __post_init__(self) -> None:
        self.metric = Metric.from_measurement(self.measurement)


# The TypeVar shows mypy that measurement{1,2} have to of the same type, the
# bound-parameter specifies that this type must be a UsageMeasurement or a subclass
MT = TypeVar("MT", bound=UsageMeasurement)


def calculate_credits(measurement1: MT, measurement2: MT) -> float:
    """
    High-level function to calculate the credits based on the differences of the two
    usage measurements.

    Will sort the two measurements according to their timestamp and use the `usage_type`
    instance of the **more recent** measurement to calculate the credits.

    :return: Non-negative amount of credits
    :raises CalculationResultError: If the amount credits would be negative
    """
    if measurement1.timestamp < measurement2.timestamp:
        older_measurement, new_measurement = measurement1, measurement2
    else:
        older_measurement, new_measurement = measurement2, measurement1

    credits = new_measurement.metric._calculate_credits(
        current_measurement=new_measurement, older_measurement=older_measurement
    )
    if credits < 0:
        raise CalculationResultError(
            f"Credits calculation of {measurement1} and {measurement2} returned a "
            "negative amount of credits."
        )
    return credits
