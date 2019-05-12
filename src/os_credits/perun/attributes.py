from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .base_attributes import (
    PERUN_DATETIME_FORMAT,
    ContainerPerunAttribute,
    CreditTimestamps,
    ReadOnlyScalarPerunAttribute,
    ScalarPerunAttribute,
    ToEmails,
)
from .exceptions import DenbiCreditsGrantedMissing

PERUN_NAMESPACE_OPT = "urn:perun:group:attribute-def:opt"
PERUN_NAMESPACE_DEF = "urn:perun:group:attribute-def:def"
PERUN_NAMESPACE_GROUP_RESOURCE_OPT = "urn:perun:group_resource:attribute-def:opt"


class DenbiCreditsUsed(
    ScalarPerunAttribute[Optional[Decimal]],
    perun_id=3382,
    perun_friendly_name="denbiCreditsCurrent",
    perun_type="java.lang.String",
    perun_namespace=PERUN_NAMESPACE_OPT,
):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def perun_deserialize(self, value: Optional[str]) -> Optional[Decimal]:
        """Stored as str inside perun, unfortunately"""
        return Decimal(value) if value else None

    def perun_serialize(self, value: Optional[Decimal]) -> Optional[str]:
        return None if value is None else str(value)


class DenbiCreditsGranted(
    ReadOnlyScalarPerunAttribute[int],
    perun_id=3383,
    perun_friendly_name="denbiCreditsGranted",
    perun_type="java.lang.String",
    perun_namespace=PERUN_NAMESPACE_OPT,
):
    """Contains the amount of credits granted to the project when its application was
    confirmed.

    Expected to be an integer and implemented read-only since we **MUST** never change
    it since the Cloud portal owns this value.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def perun_deserialize(self, value: Optional[str]) -> int:
        """Stored as str inside perun, unfortunately"""
        if value is None:
            raise DenbiCreditsGrantedMissing()
        return int(value)

    def perun_serialize(self, value: int) -> str:
        """Stored as str inside perun, unfortunately"""
        return str(value)


class ToEmail(
    ContainerPerunAttribute[ToEmails],
    perun_id=2020,
    perun_friendly_name="toEmail",
    perun_type="java.util.ArrayList",
    perun_namespace=PERUN_NAMESPACE_DEF,
):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def perun_deserialize(self, value: Optional[List[str]]) -> ToEmails:
        # see explanation in DenbiCreditTimestamps why initialising is no problem
        return value if value else []


class DenbiCreditTimestamps(
    ContainerPerunAttribute[CreditTimestamps],
    perun_id=3386,
    perun_friendly_name="denbiCreditTimestamps",
    perun_type="java.util.LinkedHashMap",
    perun_namespace=PERUN_NAMESPACE_GROUP_RESOURCE_OPT,
):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def perun_deserialize(self, value: Optional[Dict[str, str]]) -> CreditTimestamps:
        """Decodes the HashMap stored inside Perun and eases setting timestamps in case
        the attribute did not exist yet"""

        """Creating the empty dictionary although no value is stored inside Perun is
        no problem, since its contents will not be send to perun during save unless
        any changes of its content (only adding in this case) have been done"""
        measurement_timestamps = {}
        if value is not None:
            for measurement_str, timestamp_str in value.items():
                measurement_timestamps.update(
                    {
                        measurement_str: datetime.strptime(
                            timestamp_str, PERUN_DATETIME_FORMAT
                        )
                    }
                )
        return measurement_timestamps

    @classmethod
    def perun_serialize(cls, value: CreditTimestamps) -> Dict[str, str]:
        return {
            measurement: timestamp.strftime(PERUN_DATETIME_FORMAT)
            for measurement, timestamp in value.items()
        }
