from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from os_credits.exceptions import DenbiCreditsGrantedMissing

__all__ = ["DenbiCreditTimestamps", "DenbiCreditsCurrent", "ToEmails"]

PERUN_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
PERUN_NAMESPACE_OPT = "urn:perun:group:attribute-def:opt"
PERUN_NAMESPACE_DEF = "urn:perun:group:attribute-def:def"
PERUN_NAMESPACE_GROUP_RESOURCE_OPT = "urn:perun:group_resource:attribute-def:opt"


CreditTimestamps = Dict[str, datetime]
ToEmails = List[str]

# ValueType
VT = TypeVar("VT")
# ContainerValueType, used to ensure type checker, that the classes defined a `.copy`
# method
CVT = TypeVar("CVT", ToEmails, CreditTimestamps)


registered_attributes: Dict[str, Type[PerunAttribute[Any]]] = {}


class PerunAttribute(Generic[VT]):
    displayName: str
    # writable: bool
    _value: VT
    # valueModifiedAt: datetime

    # mapping between the name of a subclass of PerunAttribute and the actual class
    # object, needed to determine the class of a requested attribute of a group, see
    # groupsManager.Group

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
        if cls.__name__.startswith("_"):
            return
        registered_attributes.update({cls.__name__: cls})

    def __init__(self, value: Any, **kwargs: Any) -> None:
        """
        lala

        """
        self._value = self.perun_decode(value)
        # non-true value means that the attribute does not exist inside perun so there
        # are no further subattributes to decode
        if not self._value:
            return
        for attribute_attr_name in PerunAttribute.__annotations__:
            # ignore any non public attributes here, such as _subattr_decoder
            if attribute_attr_name.startswith("_"):
                continue
            # check whether any parser function is defined and apply it if so
            try:
                if attribute_attr_name in PerunAttribute._subattr_decoder:
                    attribute_attr_value = PerunAttribute._subattr_decoder[
                        attribute_attr_name
                    ](kwargs[attribute_attr_name])
                else:
                    attribute_attr_value = kwargs[attribute_attr_name]
            except KeyError:
                # should only happen in offline mode where e.g. displayMode is not
                # transmitted by Perun
                attribute_attr_value = None
            self.__setattr__(attribute_attr_name, attribute_attr_value)

    def to_perun_dict(self) -> Dict[str, Any]:
        """Serialize the attribute into a dictionary which can passed as JSON content to
        the perun API"""
        return {
            "value": self.perun_encode(self._value),
            "namespace": self.namespace,
            "id": self.id,
            "friendlyName": self.friendlyName,
            "type": self.type,
        }

    def perun_decode(self, value: Any) -> Any:
        return value

    def perun_encode(self, value: Any) -> Any:
        return value

    @classmethod
    def is_resource_bound(cls) -> bool:
        """
        Whether this attribute is not only bound to one specific group but a combination
        of group and resource.
        """
        return "group_resource" in cls.namespace.split(":")

    @property
    def has_changed(self) -> bool:
        """
        Whether the `value` of this attribute has been changed since creation.

        Exposed as function to enable overwriting in subclasses.
        """
        return self._updated

    @has_changed.setter
    def has_changed(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError("`has_changed` must be of type bool.")
        self._updated = value

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        # This assumes that either the container value evaluates to false or in the
        # scalar case that the attribute is None
        if not self._value:
            return f"{type(self).__name__}(value=None)"
        param_repr: List[str] = [f"value={self._value}"]
        for attribute in filter(
            lambda attribute: not attribute.startswith("_"), self.__annotations__.keys()
        ):
            # None of the values are set in offline mode
            if attribute in dir(self):
                param_repr.append(f"{attribute}={repr(getattr(self, attribute))}")

        return f"{type(self).__name__}({','.join(param_repr)})"

    def __bool__(self) -> bool:
        return bool(self._value)


class _ScalarPerunAttribute(
    PerunAttribute[VT],
    # class definition must contain the following attributes to allow 'passthrough' from
    # child classes
    perun_id=None,
    perun_friendly_name=None,
    perun_type=None,
    perun_namespace=None,
):
    """
    Base class for scalar attributes, where `value` only contains a scalar value, i.e.
    an `float` or `str`, in contrast to container attributes
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @property
    def value(self) -> VT:
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


class _ContainerPerunAttribute(
    PerunAttribute[CVT],
    # class definition must contain the following attributes to allow 'passthrough' from
    # child classes
    perun_id=None,
    perun_friendly_name=None,
    perun_type=None,
    perun_namespace=None,
):
    """
    Base class for container attributes, i.e. ToEmails where the `value` is a list of
    the actual mail addresses.

    The `has_changed` logic of PerunAttribute has to be overwritten for this classes
    since any changes during runtime are not reflected by updating `value` as an
    attribute but by updating its contents. Therefore `value` does not have a setter.
    """

    _value: CVT
    _value_copy: CVT

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # the super class will set self._value and we will save a copy here
        # also ensures that `value` of a container attribute will never be None
        self._value_copy = self._value.copy()

    @property
    def has_changed(self) -> bool:
        """
        Since the value of this attribute is a dictionary the setter approach of the
        superclass to detect changes does not work. Instead we compare the current
        values with the initial ones.
        """
        return self._value_copy != self._value

    @has_changed.setter
    def has_changed(self, value: bool) -> None:
        if not value:
            # reset changed indicator
            self._value_copy = self._value.copy()
            return
        raise ValueError("Manually setting to true not supported")

    @property
    def value(self) -> CVT:
        return self._value


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
