"""
Exceptions which might be raised during the communication with Perun or processing data
received by it.
"""


class CreditsError(Exception):
    """Base Exception for any exceptions defined by this module"""

    pass


class GroupAttributeError(CreditsError):
    """Base Exception if any Group-Attribute has an invalid value"""

    pass


class DenbiCreditsCurrentError(GroupAttributeError):
    "Raised if a group does not have any value for DenbiCreditsCurrent"
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
