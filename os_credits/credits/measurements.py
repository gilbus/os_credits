from __future__ import annotations


from enum import Enum, unique
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InfluxMeasurement:
    timestamp: datetime
    type: MeasurementType
    value: float

    def __str__(self) -> str:
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')} {self.type.name} '{self.value}'"


@unique
class MeasurementType(Enum):
    """
    Defines any kind of measurement used for credits calculation for type safety.

    The values **must** be the same as defined by the prometheus exporter.
    """

    CPU = "project_vcpu_usage"
    RAM = "project_mb_usage"
