from .measurements import UsageMeasurement, MeasurementType


def calculate_credits(measurement: UsageMeasurement, usage_last: float) -> float:
    """
    Calculate the used credits, given the measurement and the usage values.

    This function encapsulates the calculations of every measurement.
    :return: A positive floating number representing the number of credits to bill.
    """

    if measurement.type is MeasurementType.CPU:
        return _calculate_cpu(usage_last, measurement.value)
    elif measurement.type is MeasurementType.RAM:
        return _calculate_memory_mb(usage_last, measurement.value)
    raise TypeError("Passed measurement is not valid.")


def _calculate_memory_mb(usage_last: float, usage_current: float) -> float:
    CREDITS_PER_MB_HOUR = 0.3
    # return 3
    return (usage_current - usage_last) * CREDITS_PER_MB_HOUR


def _calculate_cpu(usage_last: float, usage_current: float) -> float:
    CREDITS_PER_VCPU_HOUR = 1
    # return 2
    return (usage_current - usage_last) * CREDITS_PER_VCPU_HOUR
