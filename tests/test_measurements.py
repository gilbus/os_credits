from datetime import datetime, timedelta

import pytest

from os_credits.credits.measurements import Measurement, calculate_credits
from os_credits.exceptions import CalculationResultError, MeasurementError


class TestMeasurements:
    class MeasurementToFail(
        Measurement, prometheus_name="test_fail1", friendly_name="test_fail1"
    ):
        CREDITS_PER_HOUR = None

    class Measurement1(Measurement, prometheus_name="test2", friendly_name="test2"):
        CREDITS_PER_HOUR = 1

    class Measurement2(Measurement, prometheus_name="test3", friendly_name="test3"):
        def _calculate_credits(self, *, older_measurement):
            return -10

    def test_supported_measurements_error(self):
        with pytest.raises(ValueError):
            Measurement.create_measurement("definitelyNotSupported", None, None)
        assert not Measurement.is_supported("definitelyNotSupported")

    def test_internal_calculate_credits(self):
        now = datetime.now()
        m1 = Measurement.create_measurement("test_fail1", None, now)
        with pytest.raises(TypeError):
            # Measurements must be of same type
            m1._calculate_credits(older_measurement=None)
        m1 = Measurement.create_measurement("test2", 100.0, now)
        m2 = Measurement.create_measurement("test2", 110.0, now + timedelta(hours=1))
        with pytest.raises(MeasurementError):
            # Fails since m2 is NEWER instead of older
            m1._calculate_credits(older_measurement=m2)

    def test_public_calculate_credits(self):
        now = datetime.now()
        m1 = Measurement.create_measurement("test_fail1", None, now)
        with pytest.raises(ValueError):
            # This fails due to CREDITS_PER_HOUR being None, which is also the default
            # value as per base class
            calculate_credits(m1, m1)
        m1.CREDITS_PER_HOUR = 0
        with pytest.raises(ValueError):
            # This fails due to CREDITS_PER_HOUR being non-positive
            calculate_credits(m1, m1)
        now = datetime.now()
        m1 = Measurement.create_measurement("test2", 100.0, now)
        m2 = Measurement.create_measurement("test2", 110.0, now + timedelta(hours=1))
        # test actual credits calculation
        assert (
            calculate_credits(m1, m2) == calculate_credits(m2, m1) == 10
        ), "Actual credits calculation, automatically determining older measurement"

        m1 = Measurement.create_measurement("test3", 100.0, now)
        m2 = Measurement.create_measurement("test3", 110.0, now + timedelta(hours=1))
        with pytest.raises(CalculationResultError):
            # this fails due to the custom `calculate_credits` function returning a
            # negative amount of credits to bill
            calculate_credits(m1, m2)
