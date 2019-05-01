from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Generic, List, Type, TypeVar, Union

IVT = TypeVar("IVT", bool, float, str, int)
TYPES: Dict[str, Type[InfluxValueType]] = {}


def get_influxdb_converter(type: Union[str, Type[Any]]) -> Type[InfluxValueType]:
    type_name = type
    if not isinstance(type_name, str):
        type_name = type_name.__name__
    return TYPES[type_name]


class InfluxValueType(Generic[IVT]):
    def __init_subclass__(cls, types: List[str]):
        """Used to register new ValueTypes with their supported type.
        
        Subclass in your own application to support your custom datatypes.

        :param type_: Types as reported by :func:`dataclasses.fields` for which ``cls``
            provides decode and encode support.
        """
        global TYPES
        for type_ in types:
            TYPES[type_] = cls

    @staticmethod
    def encode(value: Any) -> IVT:
        """Encodes the given value to a type which is supported natively by InfluxDB.
        """
        raise NotImplementedError("Must be implemented by subclass")

    @staticmethod
    def decode(value: Any) -> Any:
        """Decodes a value stored inside the InfluxDB or from the InfluxDB Line Protocol
        to its proper python type.
        """
        return value


class StringValueType(InfluxValueType[str], types=["str"]):
    @staticmethod
    def encode(value: Any) -> str:
        return str(value)


class IntValueType(InfluxValueType[int], types=["int"]):
    @staticmethod
    def encode(value: Any) -> int:
        return int(value)

    @staticmethod
    def decode(value: Any) -> int:
        return int(value)


class FloatValueType(InfluxValueType[float], types=["float"]):
    @staticmethod
    def encode(value: Any) -> float:
        return float(value)

    @staticmethod
    def decode(value: Any) -> float:
        return float(value)


class DecimalValueType(InfluxValueType[float], types=["Decimal"]):
    @staticmethod
    def encode(value: Any) -> float:
        return float(value)

    @staticmethod
    def decode(value: Any) -> Decimal:
        return Decimal(value)


class BoolValueType(InfluxValueType[bool], types=["bool"]):
    @staticmethod
    def encode(value: Any) -> bool:
        return bool(value)

    @staticmethod
    def decode(value: Any) -> bool:
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


class TimeValueType(InfluxValueType[int], types=["date", "datetime"]):
    @staticmethod
    def encode(value: datetime) -> int:
        return int(value.timestamp() * 1e9)

    @staticmethod
    def decode(value: Any) -> datetime:
        # does lose some preciseness unfortunately, but only nanoseconds
        return datetime.fromtimestamp(int(value) / 1e9)
