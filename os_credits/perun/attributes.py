from __future__ import annotations


from typing import TypeVar, Any, Dict, Callable, Generic, List, Type, Optional
from datetime import datetime
from logging import getLogger

from ..credits.measurements import Measurement

ValueType = TypeVar("ValueType")

PERUN_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
PERUN_NAMESPACE_OPT = "urn:perun:group:attribute-def:opt"
PERUN_NAMESPACE_DEF = "urn:perun:group:attribute-def:def"

_logger = getLogger(__name__)


class PerunAttribute(Generic[ValueType]):
    displayName: str
    description: str
    writable: bool
    _value: ValueType
    valueModifiedAt: datetime

    # mapping between the name of a subclass of PerunAttribute and the actual class
    # object, needed to determine the class of a requested attribute of a group, see
    # groupsManager.Group
    _registered_attributes: Dict[str, Type[PerunAttribute[ValueType]]] = {}

    # decoder functions for the subattribute of an Attribute
    _subattr_decoder: Dict[str, Callable[[str], Any]] = {
        "valueModifiedAt": lambda value: datetime.strptime(
            value, PERUN_DATETIME_FORMAT
        ),
        "id": int,
    }

    _updated = False

    def __init_subclass__(
        cls,
        perun_id: int,
        perun_friendly_name: str,
        perun_type: str,
        perun_namespace: str
        # perun_namespace: str,
    ) -> None:
        super().__init_subclass__()
        cls.friendlyName = perun_friendly_name
        cls.id = perun_id
        cls.type = perun_type
        cls.namespace = perun_namespace
        PerunAttribute._registered_attributes.update({cls.__name__: cls})

    def __init__(self, value: Any, **kwargs) -> None:
        """
        lala

        """
        self._value = self.perun_decode(value)
        # non-bool value means that the attribute does not exist inside perun so there
        # are no further subattribute to decode
        if not self._value:
            return
        for attribute_attr_name in PerunAttribute.__annotations__:
            # ignore any non public attributes here, such as _parser_funcs
            if attribute_attr_name.startswith("_"):
                continue
            # check whether any parser function is defined and apply it if so
            if attribute_attr_name in PerunAttribute._subattr_decoder:
                attribute_attr_value = PerunAttribute._subattr_decoder[
                    attribute_attr_name
                ](kwargs[attribute_attr_name])
            else:
                attribute_attr_value = kwargs[attribute_attr_name]
            self.__setattr__(attribute_attr_name, attribute_attr_value)

    def to_perun_dict(self) -> Dict[str, Any]:
        """Serialize the attribute into a dictionary which can passed as JSON content to
        the perun API"""
        return {
            "value": self.perun_encode(self.value),
            "namespace": self.namespace,
            "id": self.id,
            "friendlyName": self.friendlyName,
            "type": self.type,
        }

    @property
    def perun_attr_name(self) -> str:
        return f"{self.namespace}:{self.friendlyName}"

    def perun_decode(self, value: Any) -> Any:
        return value

    def perun_encode(self, value: Any) -> Any:
        return value

    @property
    def has_changed(self) -> bool:
        """
        Whether the `value` of this attribute has been changed since creation.

        Exposed as function to enable overwriting in subclasses.
        """
        return self._updated

    @has_changed.setter
    def has_changed(self, value: bool) -> None:
        self._updated = bool(value)

    @property
    def value(self) -> Optional[ValueType]:
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        # only check for type correctness if we already have a value
        if self._value and not isinstance(value, type(self._value)):
            raise TypeError(
                f"Value must be of the same type as current one ({type(self.value)})"
            )
        if self.value != value:
            self._updated = True
            self._value = value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        if self.value is None:
            return f"{type(self).__name__}(value=None)"
        param_repr: List[str] = [f"value={self.value}"]
        for attribute in filter(
            lambda attribute: not attribute.startswith("_"), self.__annotations__.keys()
        ):
            param_repr.append(f"{attribute}={repr(self.__getattribute__(attribute))}")

        return f"{type(self).__name__}({','.join(param_repr)})"

    def __bool__(self) -> bool:
        return bool(self.value)


class DenbiCreditsCurrent(
    PerunAttribute[Optional[float]],
    perun_id=3382,
    perun_friendly_name="denbiCreditsCurrent",
    perun_type="java.lang.String",
    perun_namespace=PERUN_NAMESPACE_OPT,
):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def perun_decode(self, value: Optional[str]) -> Optional[float]:
        """Stored as str inside perun, unfortunately"""
        return float(value) if value else None

    def perun_encode(self, value: Optional[float]) -> Optional[str]:
        return str(value) if value else None


class DenbiCreditsGranted(
    PerunAttribute[Optional[int]],
    perun_id=3383,
    perun_friendly_name="denbiCreditsGranted",
    perun_type="java.lang.String",
    perun_namespace=PERUN_NAMESPACE_OPT,
):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def perun_decode(self, value: Optional[str]) -> Optional[float]:
        """Stored as str inside perun, unfortunately"""
        return float(value) if value else None

    def perun_encode(self, value: Optional[float]) -> Optional[str]:
        """Stored as str inside perun, unfortunately"""
        return str(value) if value else None


class DenbiCreditsTimestamp(
    PerunAttribute[Optional[datetime]],
    perun_id=3384,
    perun_friendly_name="denbiCreditsTimestamp",
    perun_type="java.lang.String",
    perun_namespace=PERUN_NAMESPACE_OPT,
):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def perun_decode(self, value: Optional[str]) -> Optional[datetime]:
        return datetime.strptime(value, PERUN_DATETIME_FORMAT) if value else None

    def perun_encode(self, value: Optional[datetime]) -> Optional[str]:
        return value.strftime(PERUN_DATETIME_FORMAT) if value else None


class ToEmail(
    PerunAttribute[Optional[List[str]]],
    perun_id=2020,
    perun_friendly_name="toEmail",
    perun_type="java.util.ArrayList",
    perun_namespace=PERUN_NAMESPACE_DEF,
):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


CreditsTimestamps = Dict[Measurement, datetime]


class DenbiCreditsTimestamps(
    PerunAttribute[CreditsTimestamps],
    # TODO: Currently misusing the project history until we have our real HashMap
    perun_id=3362,
    perun_friendly_name="denbiProjectHistory",
    perun_type="java.util.LinkedHashMap",
    perun_namespace=PERUN_NAMESPACE_OPT,
):
    def __init__(self, **kwargs) -> None:
        self._value_copy: Optional[CreditsTimestamps] = None
        super().__init__(**kwargs)

    def perun_decode(self, value: Optional[Dict[str, str]]) -> CreditsTimestamps:
        measurement_timestamps = {}
        if value is not None:
            for measurement_str, timestamp_str in value.items():
                measurement_timestamps.update(
                    {
                        Measurement(measurement_str): datetime.strptime(
                            timestamp_str, PERUN_DATETIME_FORMAT
                        )
                    }
                )
        self._value_copy = measurement_timestamps.copy()
        return measurement_timestamps

    @classmethod
    def perun_encode(cls, value: CreditsTimestamps) -> Dict[str, str]:
        return {
            measurement.value: timestamp.strftime(PERUN_DATETIME_FORMAT)
            for measurement, timestamp in value.items()
        }

    @property
    def has_changed(self) -> bool:
        """
        Since the value of this attribute is a dictionary the setter approach of the
        superclass to detect changes does not work. Instead we compare the current
        values with the initial ones.
        """
        return self._value_copy != self.value

    @has_changed.setter
    def has_changed(self, value: bool) -> None:
        if not value:
            self._value_copy = self._value.copy() if self._value else None
            return
        raise ValueError("Manually setting to true not supported")
