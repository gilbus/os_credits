"""Provides helper classes and functions to serialize and deserialize python data types
into basic ones support by *InfluxDB*.
For example if we'd like to store :class:`~fractions.Fraction` one basic way could be
the following:

>>> from os_credits.influx.helper import InfluxSerializer, serialize, deserialize
>>> from fractions import Fraction
>>> class FractionSerializer(InfluxSerializer, types=["Fraction"]):
...     @staticmethod
...     def serialize(value: Fraction) -> str:
...         return f"{value.numerator}/{value.denominator}"
...     @staticmethod
...     def deserialize(value: str) -> Fraction:
...         numerator_str, denominator_str = value.split('/')
...         return Fraction(int(numerator_str), int(denominator_str))
>>> f = Fraction(1, 4)
>>> serialize(f)
'1/4'
>>> deserialize('1/4', Fraction)
Fraction(1, 4)

See :class:`~os_credits.credits.base_models.Credits` for another example. The high level
functions :func:`~os_credits.influx.helper.serialize` and
:func:`~os_credits.influx.helper.deserialize` determine which serializer is responsible
for the provided value.

"""
from __future__ import annotations

from dataclasses import Field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type, Union

_InfluxDataTypes = Union[bool, float, str, int]
_registered_serializers: Dict[str, Type[InfluxSerializer]] = {}


def serialize(
    value: Any, field_or_type: Optional[Union[Field, Type[Any]]] = None
) -> _InfluxDataTypes:
    """Determines the correct subclass of :class:`InfluxSerializer` with the help of
    :attr:`field` and calls its :func:`encode` method to convert the given value into a
    datatype natively supported by *InfluxDB*.

    One usage is the conversion of python datetime objects into timestamps with
    (simulated) nanosecond precision. This methods are automatically invoked by
    :class:`~os_credits.influx.model.InfluxDBPoint`.

    :param value: Value to encode. 
    :param field_or_type: Either a :class:`~dataclasses.Field` object of which we
    require the `type` information, which should be a string since we use ``from
    __future__ import annotations`` (available for Python3.7+) but the older case of
    classes is also supported.  Alternatively the raw type to use for encoding. If not
    specified ``type(value)`` is used instead.
    :return: Encoded value
    """
    # TODO: This prevents `None` from being specified as type
    if field_or_type is None:
        type_name = type(value).__name__
    else:
        if isinstance(field_or_type, Field):
            if not isinstance(field_or_type.type, str):
                type_name = field_or_type.type.__name__
            else:
                type_name = field_or_type.type
        else:
            type_name = field_or_type.__name__
    try:
        serializer = _registered_serializers[type_name]
    except KeyError:
        raise TypeError(f"No converter registered for type {type_name}.")
    return serializer.serialize(value)


def deserialize(value: Any, field_or_type: Union[Field, Type[Any]]) -> Any:
    """Determines the correct subclass of :class:`InfluxSerializer` with the help of
    :attr:`field` and calls its :func:`decode` method to convert the given value into
    the python datatype indicated by ``field.type``.

    If we are decoding an *InfluxDB Line* :attr:`value` will always be a :class:`str`
    but if we are called from
    :func:`~os_credits.influx.model.InfluxDBPoint.from_iterpoint` it can be any value of
    :attr:`InfluxValueType`. Additional decoding allows for storing more abstract data types inside
    the *InfluxDB* such as datetime objects.

    :param value: Value to encode. 
    :param field_or_type: Either a :class:`~dataclasses.Field` object of which we
    require the `type` information, which should be a string since declare ``from
    __future__ import annotations`` but the older case of classes is also supported.
    Alternatively the raw type to use for encoding.
    :return: Encoded value
    """
    if isinstance(field_or_type, Field):
        if not isinstance(field_or_type.type, str):
            type_name = field_or_type.type.__name__
        else:
            type_name = field_or_type.type
    else:
        type_name = field_or_type.__name__
    try:
        serializer = _registered_serializers[type_name]
    except KeyError:
        raise TypeError(f"No converter registered for type {type_name}.")
    return serializer.deserialize(value)


class InfluxSerializer:
    """Base class for all serializers. Subclass in your own application to support your
    custom data types.     """

    def __init_subclass__(cls, types: List[str]):
        """Used to register new serializers with their supported type.


        :param types: Types as reported by :func:`dataclasses.fields` for which ``cls``
            provides decode and encode support.
        """
        for type_ in types:
            _registered_serializers[type_] = cls

    @staticmethod
    def serialize(value: Any) -> _InfluxDataTypes:
        """Encodes the given value to a type which is supported natively by InfluxDB.
        """
        raise NotImplementedError("Must be implemented by subclass")

    @staticmethod
    def deserialize(value: _InfluxDataTypes) -> Any:
        """Decodes a value stored inside the InfluxDB or from the InfluxDB Line Protocol
        to its proper python type.
        """
        return value


class _StringSerializer(InfluxSerializer, types=["str"]):
    @staticmethod
    def serialize(value: Any) -> str:
        return str(value)


class _IntSerializer(InfluxSerializer, types=["int"]):
    @staticmethod
    def serialize(value: Any) -> int:
        return int(value)

    @staticmethod
    def deserialize(value: Any) -> int:
        return int(value)


class _FloatSerializer(InfluxSerializer, types=["float"]):
    @staticmethod
    def serialize(value: Any) -> float:
        return float(value)

    @staticmethod
    def deserialize(value: Any) -> float:
        return float(value)


class _DecimalSerializer(InfluxSerializer, types=["Decimal"]):
    @staticmethod
    def serialize(value: Any) -> float:
        return float(value)

    @staticmethod
    def deserialize(value: Any) -> Decimal:
        return Decimal(value)


class _BoolSerializer(InfluxSerializer, types=["bool"]):
    @staticmethod
    def serialize(value: Any) -> bool:
        return bool(value)

    @staticmethod
    def deserialize(value: Any) -> bool:
        """InfluxDB knows multiple ways to express a boolean value"""
        # also including True and False since ``value`` will already be a bool when
        # using the input from ``iterpoints``
        true_values = {"t", "T", "true", "True", "TRUE", True}
        false_values = {"f", "F", "false", "False", "FALSE", False}
        if value in true_values:
            return True
        elif value in false_values:
            return False
        else:
            raise ValueError("Unknown bool representation")
        return True if value in true_values else False


class _DatetimeSerializer(InfluxSerializer, types=["datetime"]):
    @staticmethod
    def serialize(value: datetime) -> int:
        return int(value.timestamp() * 1e9)

    @staticmethod
    def deserialize(value: Any) -> datetime:
        # does lose some preciseness unfortunately, but only nanoseconds
        return datetime.fromtimestamp(int(value) / 1e9)
