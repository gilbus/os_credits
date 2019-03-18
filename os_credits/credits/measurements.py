from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar

from os_credits.exceptions import CalculationResultError, MeasurementError


class Measurement:
    timestamp: datetime
    value: float
    _measurement_types: Dict[str, Type[Measurement]] = {}

    CREDITS_PER_HOUR: Optional[float] = None
    property_description = ""

    def __init_subclass__(cls, prometheus_name: str, friendly_name: str) -> None:
        Measurement._measurement_types.update({prometheus_name: cls})
        cls.prometheus_name = prometheus_name
        cls.friendly_name = friendly_name

    @classmethod
    def create_measurement(
        cls, prometheus_name: str, value: float, timestamp: datetime
    ) -> Measurement:
        try:
            measurement = cls._measurement_types[prometheus_name]()
        except KeyError:
            raise ValueError(
                f"Measurement `{prometheus_name}` it not supported/needed."
            )
        measurement.value = value
        measurement.timestamp = timestamp
        return measurement

    @classmethod
    def is_supported(cls, prometheus_name: str) -> bool:
        return prometheus_name in cls._measurement_types

    def _calculate_credits(self, *, older_measurement: Measurement) -> float:
        if not isinstance(older_measurement, type(self)):
            raise TypeError("Measurements must be of same type")
        if self.CREDITS_PER_HOUR is None or self.CREDITS_PER_HOUR <= 0:
            raise ValueError(
                f"Measurement type {type(self)} does neither define a positive "
                "`CREDITS_PER_HOUR` nor overwrites `calculate_credits`"
            )
        if self.timestamp < older_measurement.timestamp:
            raise MeasurementError(
                "Passed measurement must be older. Use the top-level "
                "`calculate_credits` function to prevent this error."
            )
        return (self.value - older_measurement.value) * self.CREDITS_PER_HOUR

    @classmethod
    def api_information(cls) -> Dict[str, Any]:
        """
        Returns a dictionary containing the description and type information of this
        measurement.

        This is just a simple base implementation and should be overridden by subclasses
        if necessary.
        """
        # if not self.CREDITS_PER_HOUR:
        #    raise NotImplementedError(
        #        "Not setting CREDITS_PER_HOUR requires overwriting `api_information`"
        #    )
        return {"type": "int", "description": cls.property_description}

    def __str__(self) -> str:
        return (
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')}-"
            f"{self.prometheus_name}:'{self.value}'"
        )


# The TypeVar shows mypy that measurement{1,2} have to of the same type, the
# bound-parameter specifies that this type must be a Measurement or a subclass
MT = TypeVar("MT", bound=Measurement)


def calculate_credits(measurement1: MT, measurement2: MT) -> float:
    if measurement1.timestamp < measurement2.timestamp:
        older_measurement, new_measurement = measurement1, measurement2
    else:
        older_measurement, new_measurement = measurement2, measurement1

    credits = new_measurement._calculate_credits(older_measurement=older_measurement)
    if credits < 0:
        raise CalculationResultError(
            f"Credits calculation of {measurement1} and {measurement2} returned a "
            "negative amount of credits."
        )
    return credits


class _VCPUUsage(
    Measurement, prometheus_name="project_vcpu_usage", friendly_name="cpu"
):

    CREDITS_PER_HOUR = 1
    property_description = "Amount of vCPUs."


class _RAMUsage(Measurement, prometheus_name="project_mb_usage", friendly_name="ram"):

    CREDITS_PER_HOUR = 0.3
    property_description = "Amount of RAM in MB."
