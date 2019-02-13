from .measurements import MeasurementType, UsageMeasurement


def calculate_credits(
    *, current_measurement: UsageMeasurement, last_measurement: UsageMeasurement
) -> float:
    """
    Calculate the used credits, given the current and last measurement.

    This function encapsulates the calculations of every measurement. Due to the
    identical types and the dangers of confounding the arguments keyword-arguments are
    enforced.
    :return: A non-negative floating number representing the number of credits to bill.
    """

    if current_measurement.type is MeasurementType.CPU:
        return _calculate_cpu(
            current_measurement=current_measurement, last_measurement=last_measurement
        )
    elif current_measurement.type is MeasurementType.RAM:
        return _calculate_memory_mb(
            current_measurement=current_measurement, last_measurement=last_measurement
        )
    raise TypeError("Passed current_measurement is not valid.")


def _calculate_memory_mb(
    current_measurement: UsageMeasurement, last_measurement: UsageMeasurement
) -> float:
    CREDITS_PER_MB_HOUR = 0.3
    return (current_measurement.value - last_measurement.value) * CREDITS_PER_MB_HOUR


def _calculate_cpu(
    current_measurement: UsageMeasurement, last_measurement: UsageMeasurement
) -> float:
    CREDITS_PER_VCPU_HOUR = 1
    return (current_measurement.value - last_measurement.value) * CREDITS_PER_VCPU_HOUR
