from __future__ import annotations


from enum import Enum, unique
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InfluxMeasurement:
    timestamp: datetime
    type: Measurement
    value: float

    def __str__(self) -> str:
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')} {self.type.name} '{self.value}'"


@unique
class Measurement(Enum):
    """
    Defines any kind of measurement used for credits calculation for type safety.

    The values **must** be the same as defined by the prometheus exporter.
    """

    CPU = "project_vcpu_usage"
    RAM = "project_mb_usage"


def calculate_credits(measurement: InfluxMeasurement, usage_last: float) -> float:
    """
    Calculate the used credits, given the measurement and the usage values.

    This function encapsulates the calculations of every measurement.
    :return: A positive floating number representing the number of credits to bill.
    """

    if measurement.type is Measurement.CPU:
        return _calculate_cpu(usage_last, measurement.value)
    elif measurement.type is Measurement.RAM:
        return _calculate_memory_mb(usage_last, measurement.value)
    raise TypeError("Passed measurement is not valid.")


def _calculate_memory_mb(usage_last: float, usage_current: float) -> float:
    CREDITS_PER_MB_HOUR = 5
    return 3
    return (usage_current - usage_last) * CREDITS_PER_MB_HOUR


def _calculate_cpu(usage_last: float, usage_current: float) -> float:
    CREDITS_PER_VCPU_HOUR = 40
    return 2
    return (usage_current - usage_last) * CREDITS_PER_VCPU_HOUR
