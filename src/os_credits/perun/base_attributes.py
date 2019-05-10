from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Type, TypeVar

PERUN_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
# ValueType
VT = TypeVar("VT")


class PerunAttribute(Generic[VT]):
    """Base class of all *Perun* attributes.

    Consists of multiple "subattributes", such as :attr:`valueModifiedAt`. The most
    relevant one is ``value``.
    """

    _updated = False
    _value: VT

    registered_attributes: Dict[str, Type["PerunAttribute"[Any]]] = {}
    """Mapping between the name of a subclass of PerunAttribute and the actual class
     object, needed to determine the class of a requested attribute of a group, see
     :func:`~os_credits.perun.group.Group.get_perun_attributes`.
     """

    def __init_subclass__(
        cls,
        perun_id: int,
        perun_friendly_name: str,
        perun_type: str,
        perun_namespace: str,
    ) -> None:
        cls.friendlyName = perun_friendly_name
        cls.id = perun_id
        cls.type = perun_type
        cls.namespace = perun_namespace
        # do not register any intermediate base classes
        if cls.__name__.startswith("_"):
            return
        PerunAttribute.registered_attributes[cls.__name__] = cls

    def __init__(self, value: Any, **kwargs: Any) -> None:
        """Using kwargs since :func:`~os_credits.perun.group.Group.connect` calls us
        with all "subattributes" received from *Perun* but we are currently only
        interested in ``value``.
        """
        self._value = self.perun_decode(value)

    def to_perun_dict(self) -> Dict[str, Any]:
        """Serialize the attribute into a dictionary which can passed as JSON content to
        the perun API to identify an attribute.
        """
        return {
            "value": self.perun_encode(self._value),
            "namespace": self.namespace,
            "id": self.id,
            "friendlyName": self.friendlyName,
            "type": self.type,
        }

    @classmethod
    def get_full_name(cls) -> str:
        return f"{cls.namespace}:{cls.friendlyName}"

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


class _ReadOnlyScalarPerunAttribute(
    PerunAttribute[VT],
    # class definition must contain the following attributes to allow 'passthrough' from
    # child classes
    perun_id=None,
    perun_friendly_name=None,
    perun_type=None,
    perun_namespace=None,
):
    """
    Base class for all read-only scalar attributes, where `value` only contains a scalar
    value, i.e.  an `float` or `str`, in contrast to container attributes
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @property
    def value(self) -> VT:
        return self._value


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
    Identical to :class:`_ReadOnlyScalarPerunAttribute` but provides a setter method for
    `value`
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


ToEmails = List[str]
CreditTimestamps = Dict[str, datetime]
# ContainerValueType, used to ensure type checker, that the classes define a `.copy`
# method
CVT = TypeVar("CVT", ToEmails, CreditTimestamps)


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
