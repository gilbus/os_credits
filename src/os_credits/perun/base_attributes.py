"""Contains all subclasses of and
:class:`~os_credits.perun.base_attributes.PerunAttribute` itself but not any leaf
subclasses.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Type, TypeVar

PERUN_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
# ValueType
VT = TypeVar("VT")


class PerunAttribute(Generic[VT]):
    """Base class of all *Perun* attributes. The :class:`~typing.Generic` base class is
    used to allow attributes to specify the type of their deserialized value. This
    allows a static type checker to check for correct usage.

    Should not be extended or called directly but rather one of the other base classes
    defined in this file which extend this one. Its main task is to collect all
    available attributes via :ref:`Subclass Hooks` and make them available to
    :func:`os_credits.perun.group.Group.get_perun_attributes`.

    The actual value of an attribute is stored inside :data:`_value` and must be
    provided as :class:`property` by a subclass. Subclasses are also responsible for
    overwriting :func:`perun_serialize` and :func:`perun_deserialize` if necessary. When
    doing so they have to make sure that their deserialized version of ``value=None``,
    i.e. the attribute has currently no value inside *Perun*, such as ``0`` or ``[]``
    evaluates to false when calling ``bool(attr.value)``.

    Information such as :data:`id`, :data:`friendlyName`, :data:`type`,
    :data:`namespace` have to known inside the code since they must be sent to *Perun*
    when initially setting the value of an attribute.

    """

    _updated = False
    _value: VT

    registered_attributes: Dict[str, Type["PerunAttribute"[Any]]] = {}
    """Mapping between the name of a subclass of PerunAttribute and the actual class
     object, needed to determine the class of a requested attribute of a group, see
     :func:`~os_credits.perun.group.Group.get_perun_attributes`.
     """

    friendlyName: str
    """Human readable name of the attribute inside Perun.
    """

    id: int
    """ID of the attribute inside Perun.
    """

    type: str
    """Type of the attribute inside Perun.
    """

    namespace: str
    """Namespace of the attribute inside Perun.
    """

    def __init_subclass__(
        cls,
        perun_id: int,
        perun_friendly_name: str,
        perun_type: str,
        perun_namespace: str,
    ) -> None:
        # Only process real attribute, not intermediate base classes
        if not perun_id:
            return
        cls.friendlyName = perun_friendly_name
        cls.id = perun_id
        cls.type = perun_type
        cls.namespace = perun_namespace
        PerunAttribute.registered_attributes[cls.__name__] = cls

    def __init__(self, value: Any, **kwargs: Any) -> None:
        """Using kwargs since :func:`~os_credits.perun.group.Group.connect` calls us
        with all *subattributes* received from *Perun* but we are currently only
        interested in ``value``.

        Once other *subattributes* are needed by the code, e.g. ``value_modified_at``,
        they should be added to the function signature and set inside this constructor.
        """
        self._value = self.perun_deserialize(value)

    def to_perun_dict(self) -> Dict[str, Any]:
        """Serialize the attribute into a dictionary which can passed as JSON content to
        the perun API.
        """
        return {
            "value": self.perun_serialize(self._value),
            "namespace": self.namespace,
            "id": self.id,
            "friendlyName": self.friendlyName,
            "type": self.type,
        }

    @classmethod
    def get_full_name(cls) -> str:
        """Needed when querying specific attributes of a group instead of all of them.

        :return: Full name of the attribute inside *Perun*.
        """
        return f"{cls.namespace}:{cls.friendlyName}"

    def perun_deserialize(self, value: Any) -> Any:
        """Deserialize from the type/format used by *Perun* when converting into JSON to
        transmit the value of this attribute.

        :param value: Serialized value received by *Perun* via JSON.
        :return: Deserialized value used by application.
        """
        return value

    def perun_serialize(self, value: Any) -> Any:
        """Serialize to the type/format used by *Perun* when converting into JSON to
        transmit the value of this attribute.

        :param value: Deserialized value used by application.
        :return: Serialized value for transmission to *Perun*.
        """
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
        Whether the ``value`` of this attribute has changed since creation.
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


class ReadOnlyScalarPerunAttribute(
    PerunAttribute[VT],
    # class definition must contain the following attributes to allow 'passthrough' from
    # child classes
    perun_id=None,
    perun_friendly_name=None,
    perun_type=None,
    perun_namespace=None,
):
    """Base class for all read-only scalar attributes, where `value` only contains a
    scalar value, e.g. a `float` or `str`, in contrast to container attributes.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @property
    def value(self) -> VT:
        return self._value


class ScalarPerunAttribute(
    PerunAttribute[VT],
    # class definition must contain the following attributes to allow 'passthrough' from
    # child classes
    perun_id=None,
    perun_friendly_name=None,
    perun_type=None,
    perun_namespace=None,
):
    """
    Identical to :class:`ReadOnlyScalarPerunAttribute` but provides a setter method for
    :attr:`value` which makes sure that type of non-empty content does not change.
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
# "ContainerValueType", used by type checker, to ensure that the classes defines a
# `.copy` method
CVT = TypeVar("CVT", ToEmails, CreditTimestamps)


class ContainerPerunAttribute(
    PerunAttribute[CVT],
    # class definition must contain the following attributes to allow 'passthrough' from
    # child classes
    perun_id=None,
    perun_friendly_name=None,
    perun_type=None,
    perun_namespace=None,
):
    """
    Base class for container attributes, e.g. :data:`ToEmails` where `value` is a list
    of the actual mail addresses.

    The `has_changed` logic of PerunAttribute has to be overwritten for this classes
    since any changes are not reflected by updating `value` as an attribute but by
    updating its contents. Therefore `value` does not have a setter.

    If Perun does not have any value yet for this attribute
    :func:`~Perun.perun_deserialize` must set not it to ``None`` but to an empty
    container. This eases the handling since no checks for ``None`` are needed.

    In addition ``None`` cannot be used since we create a shallow copy of the attribute
    once it has been serialized to be able to detect changes to its values; ``None`` has
    no ``copy`` function but all several container data structures such as ``list``,
    ``dict`` and ``set`` support it. Finally it allows to us skip defining a setter for
    :attr:`value` since only its contents are allowed to change.
    """

    _value: CVT
    _value_copy: CVT

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._value_copy = self._value.copy()

    @property
    def has_changed(self) -> bool:
        """
        Since the value of this attribute is a container the setter approach of the
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
