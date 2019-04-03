from datetime import datetime, timedelta

import pytest

from os_credits.credits.measurements import Metric, UsageMeasurement, calculate_credits
from os_credits.exceptions import CalculationResultError, MeasurementError


class _TestMetric1(Metric, measurement_name="test_fail1", friendly_name="test_fail1"):
    CREDITS_PER_VIRTUAL_HOUR = None


class _TestMetric2(Metric, measurement_name="test2", friendly_name="test2"):
    CREDITS_PER_VIRTUAL_HOUR = 1


class _TestMetric3(Metric, measurement_name="test3", friendly_name="test3"):
    @classmethod
    def _calculate_credits(cls, *, current_measurement, older_measurement):
        return -10


now = datetime.now()

m1 = UsageMeasurement(
    measurement="test_fail1", location_id=0, timestamp=now, project_name="", value=0.0
)
m21 = UsageMeasurement(
    measurement="test2", value=100.0, timestamp=now, project_name="", location_id=0
)
m22 = UsageMeasurement(
    measurement="test2",
    value=110.0,
    timestamp=now + timedelta(hours=1),
    project_name="",
    location_id=0,
)


def test_supported_measurements_error():
    with pytest.raises(ValueError):
        Metric.from_measurement("definitelyNotSupported")
    assert not Metric.is_supported("definitelyNotSupported")


def test_internal_calculate_credits():
    with pytest.raises(TypeError):
        # Measurements must be of same type
        m1.metric._calculate_credits(current_measurement=m1, older_measurement=m21)
    with pytest.raises(MeasurementError):
        # Fails since m2 is NEWER instead of older
        m21.metric._calculate_credits(current_measurement=m21, older_measurement=m22)


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

    m31 = UsageMeasurement(
        measurement="test3", value=100.0, timestamp=now, project_name="", location_id=0
    )
    m32 = UsageMeasurement(
        measurement="test3",
        value=110.0,
        timestamp=now + timedelta(hours=1),
        project_name="",
        location_id=0,
    )
    with pytest.raises(CalculationResultError):
        # this fails due to the custom `calculate_credits` function returning a
        # negative amount of credits to bill
        calculate_credits(m31, m32)


def test_costs_per_hour():
    assert _TestMetric2.costs_per_hour(5) == 5
