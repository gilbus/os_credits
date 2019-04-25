from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from os_credits.exceptions import DenbiCreditsGrantedMissing

from . import PERUN_DATETIME_FORMAT
from .base_attributes import (
    CreditTimestamps,
    ToEmails,
    _ContainerPerunAttribute,
    _ScalarPerunAttribute,
)

PERUN_NAMESPACE_OPT = "urn:perun:group:attribute-def:opt"
PERUN_NAMESPACE_DEF = "urn:perun:group:attribute-def:def"
PERUN_NAMESPACE_GROUP_RESOURCE_OPT = "urn:perun:group_resource:attribute-def:opt"


class DenbiCreditsCurrent(
    _ScalarPerunAttribute[Optional[float]],
    perun_id=3382,
    perun_friendly_name="denbiCreditsCurrent",
    perun_type="java.lang.String",
    perun_namespace=PERUN_NAMESPACE_OPT,
):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def perun_decode(self, value: Optional[str]) -> Optional[float]:
        """Stored as str inside perun, unfortunately"""
        return float(value) if value else None

    def perun_encode(self, value: Optional[float]) -> Optional[str]:
        return str(value) if value else None


class DenbiCreditsGranted(
    _ScalarPerunAttribute[int],
    perun_id=3383,
    perun_friendly_name="denbiCreditsGranted",
    perun_type="java.lang.String",
    perun_namespace=PERUN_NAMESPACE_OPT,
):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def perun_decode(self, value: Optional[str]) -> int:
        """Stored as str inside perun, unfortunately"""
        if value is None:
            raise DenbiCreditsGrantedMissing()
        return int(value)

    def perun_encode(self, value: int) -> str:
        """Stored as str inside perun, unfortunately"""
        return str(value)

    # TODO: evaluate read-only mechanism


class ToEmail(
    _ContainerPerunAttribute[ToEmails],
    perun_id=2020,
    perun_friendly_name="toEmail",
    perun_type="java.util.ArrayList",
    perun_namespace=PERUN_NAMESPACE_DEF,
):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def perun_decode(self, value: Optional[List[str]]) -> ToEmails:
        # see explanation in DenbiCreditTimestamps why initialising is no problem
        return value if value else []


class DenbiCreditTimestamps(
    _ContainerPerunAttribute[CreditTimestamps],
    perun_id=3386,
    perun_friendly_name="denbiCreditTimestamps",
    perun_type="java.util.LinkedHashMap",
    perun_namespace=PERUN_NAMESPACE_GROUP_RESOURCE_OPT,
):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def perun_decode(self, value: Optional[Dict[str, str]]) -> CreditTimestamps:
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
    def perun_encode(cls, value: CreditTimestamps) -> Dict[str, str]:
        return {
            measurement: timestamp.strftime(PERUN_DATETIME_FORMAT)
            for measurement, timestamp in value.items()
        }
