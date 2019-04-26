from os_credits.exceptions import CreditsError


class PerunBaseException(CreditsError):
    "Base exception class for all errors occurring during communication with Perun"
    pass


class GroupNotExistsError(PerunBaseException):
    "Python mapping of Perun's GroupNotExistsException"
    pass


class AttributeNotExistsError(PerunBaseException):
    "Python mapping of Perun's AttributeNotExistsException"
    pass


class InternalError(PerunBaseException):
    "Python mapping of Perun's InternalErrorException"
    pass


class ConsistencyError(PerunBaseException):
    "Python mapping of Perun's ConsistencyErrorException"
    pass


class RequestError(PerunBaseException):
    "Generic Exception in case no specific exception has been thrown"
    pass


class GroupAttributeError(CreditsError):
    "Base Exception if any Group-Attribute has an invalid value"
    pass


class DenbiCreditsCurrentError(GroupAttributeError):
    """Raised if a group does not have any value for DenbiCreditsCurrent and has been
    billed before"""

    pass


class DenbiCreditsGrantedMissing(GroupAttributeError):
    """Raised if a group does not have any credits granted in which case we cannot
    operate on it."""

    pass
