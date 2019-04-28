from __future__ import annotations

from decimal import Decimal
from typing import TypeVar

from os_credits.credits.base_models import UsageMeasurement
from os_credits.exceptions import CalculationResultError
from os_credits.log import internal_logger

# The TypeVar shows mypy that measurement{1,2} have to of the same type, the
# bound-parameter specifies that this type must be a UsageMeasurement or a subclass
MT = TypeVar("MT", bound=UsageMeasurement)


def calculate_credits(measurement1: MT, measurement2: MT) -> Decimal:
    """
    High-level function to calculate the credits based on the differences of the two
    usage measurements.

    Will sort the two measurements according to their time and use the `usage_type`
    instance of the **more recent** measurement to calculate the credits.

    :return: Non-negative amount of credits
    :raises CalculationResultError: If the amount credits would be negative
    """
    if measurement1.time < measurement2.time:
        older_measurement, new_measurement = measurement1, measurement2
    else:
        older_measurement, new_measurement = measurement2, measurement1

    internal_logger.debug(
        "Billing older `%s` and current measurement `%s`",
        older_measurement,
        new_measurement,
    )
    credits = new_measurement.metric.calculate_credits(
        current_measurement=new_measurement, older_measurement=older_measurement
    )
    internal_logger.debug("Calculated credits: %f", credits)
    if credits < 0:
        raise CalculationResultError(
            f"Credits calculation of {measurement1} and {measurement2} returned a "
            "negative amount of credits."
        )
    return credits
