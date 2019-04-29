from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Type

import pytest

from os_credits.credits.base_models import Metric, TotalUsageMetric, UsageMeasurement
from os_credits.credits.billing import calculate_credits
from os_credits.credits.models import measurement_by_name
from os_credits.exceptions import CalculationResultError, MeasurementError

with pytest.raises(TypeError):
    # Due to CREDITS_PER_VIRTUAL_HOUR being None

    class _TestMetric1(TotalUsageMetric, name="test_fail1", friendly_name="test_fail1"):
        CREDITS_PER_VIRTUAL_HOUR = None


class _TestMetric2(TotalUsageMetric, name="test2", friendly_name="test2"):
    CREDITS_PER_VIRTUAL_HOUR = Decimal("1")


class _TestMetric3(TotalUsageMetric, name="test3", friendly_name="test3"):
    CREDITS_PER_VIRTUAL_HOUR = Decimal("2")

    @classmethod
    def calculate_credits(cls, *, current_measurement, older_measurement):
        return -10


@dataclass(frozen=True)
class _TestMeasurement2(UsageMeasurement):
    metric: Type[Metric] = _TestMetric2


@dataclass(frozen=True)
class _TestMeasurement3(UsageMeasurement):
    metric: Type[Metric] = _TestMetric3


now = datetime.now()

m21 = _TestMeasurement2(
    measurement="test2", value=100.0, time=now, project_name="", location_id=0
)
m22 = _TestMeasurement2(
    measurement="test2",
    value=110.0,
    time=now + timedelta(hours=1),
    project_name="",
    location_id=0,
)

m31 = _TestMeasurement3(
    measurement="test3", value=100.0, time=now, project_name="", location_id=0
)
m32 = _TestMeasurement3(
    measurement="test3",
    value=110.0,
    time=now + timedelta(hours=1),
    project_name="",
    location_id=0,
)


def test_supported_measurements_error():
    with pytest.raises(ValueError):
        measurement_by_name("definitelyNotSupported")


def test_internal_calculate_credits():
    with pytest.raises(TypeError):
        # Measurements must be of same type
        m21.metric.calculate_credits(current_measurement=m31, older_measurement=m21)
    with pytest.raises(MeasurementError):
        # Fails since m2 is NEWER instead of older
        m21.metric.calculate_credits(current_measurement=m21, older_measurement=m22)


def test_public_calculate_credits():
    # test actual credits calculation
    assert (
        10 == calculate_credits(m21, m22) == calculate_credits(m22, m21)
    ), "Actual credits calculation, automatically determining older measurement"

    with pytest.raises(CalculationResultError):
        # this fails due to the custom `calculate_credits` function returning a
        # negative amount of credits to bill
        calculate_credits(m31, m32)
