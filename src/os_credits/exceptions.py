"""
Exceptions which might be raised during the communication with Perun or processing data
received by it.
"""


class CreditsError(Exception):
    "Base Exception for any exceptions defined by this module"
    pass


class MissingInfluxDatabase(CreditsError):
    "Raised if a required database inside the InfluxDB does not exist"
    pass


class GroupAttributeError(CreditsError):
    "Base Exception if any Group-Attribute has an invalid value"
    pass


class DenbiCreditsCurrentError(GroupAttributeError):
    """Raised if a group does not have any value for DenbiCreditsCurrent and has been
    billed before"""

    pass


class MissingConfigError(CreditsError):
    "Raised if a non-set config value without default value is requested"
    pass


class MeasurementError(CreditsError):
    "Raised if the given measurements cannot be used to calculate credits usage"
    pass


class CalculationResultError(CreditsError):
    "Raised if the result of credits calculation does not meet constraints"
    pass


class RequestError(CreditsError):
    "Generic Exception in case no specific exception has been thrown"
    pass


class GroupNotExistsError(CreditsError):
    "Python mapping of Perun's GroupNotExistsException"
    pass


class AttributeNotExistsError(CreditsError):
    "Python mapping of Perun's AttributeNotExistsException"
    pass


class InternalError(CreditsError):
    "Python mapping of Perun's InternalErrorException"
    pass


class ConsistencyError(CreditsError):
    "Python mapping of Perun's ConsistencyErrorException"
    pass
