from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Type

import pytest

from os_credits.credits.base_models import Metric, UsageMeasurement
from os_credits.credits.billing import calculate_credits
from os_credits.credits.models import measurement_by_name
from os_credits.exceptions import CalculationResultError, MeasurementError


class _TestMetric1(Metric, measurement_name="test_fail1", friendly_name="test_fail1"):
    CREDITS_PER_VIRTUAL_HOUR = None


class _TestMetric2(Metric, measurement_name="test2", friendly_name="test2"):
    CREDITS_PER_VIRTUAL_HOUR = 1


class _TestMetric3(Metric, measurement_name="test3", friendly_name="test3"):
    @classmethod
    def calculate_credits(cls, *, current_measurement, older_measurement):
        return -10


@dataclass(frozen=True)
class _TestMeasurement1(UsageMeasurement):
    metric: Type[Metric] = _TestMetric1


@dataclass(frozen=True)
class _TestMeasurement2(UsageMeasurement):
    metric: Type[Metric] = _TestMetric2


@dataclass(frozen=True)
class _TestMeasurement3(UsageMeasurement):
    metric: Type[Metric] = _TestMetric3


now = datetime.now()

m1 = _TestMeasurement1(
    measurement="test_fail1", location_id=0, time=now, project_name="", value=0.0
)
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


def test_supported_measurements_error():
    with pytest.raises(ValueError):
        measurement_by_name("definitelyNotSupported")
    assert not Metric.is_supported("definitelyNotSupported")


def test_internal_calculate_credits():
    with pytest.raises(TypeError):
        # Measurements must be of same type
        m1.metric.calculate_credits(current_measurement=m1, older_measurement=m21)
    with pytest.raises(MeasurementError):
        # Fails since m2 is NEWER instead of older
        m21.metric.calculate_credits(current_measurement=m21, older_measurement=m22)


def test_public_calculate_credits(monkeypatch):
    now = datetime.now()
    with pytest.raises(ValueError):
        # This fails due to CREDITS_PER_VIRTUAL_HOUR being None, which is also the default
        # value as per base class
        calculate_credits(m1, m1)
    with monkeypatch.context() as m:
        m.setattr(m1.metric, "CREDITS_PER_VIRTUAL_HOUR", 0)
        with pytest.raises(ValueError):
            # This fails due to CREDITS_PER_VIRTUAL_HOUR being non-positive
            calculate_credits(m1, m1)
    now = datetime.now()
    # test actual credits calculation
    assert (
        calculate_credits(m21, m22) == calculate_credits(m22, m21) == 10
    ), "Actual credits calculation, automatically determining older measurement"

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
    with pytest.raises(CalculationResultError):
        # this fails due to the custom `calculate_credits` function returning a
        # negative amount of credits to bill
        calculate_credits(m31, m32)
