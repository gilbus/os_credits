"""
Implements the RPC-Calls of the GroupsManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-GroupsManager.html
"""

from __future__ import annotations

from logging import getLogger
from typing import Dict, Any, TypeVar, Generic, Callable, List
from datetime import datetime

from .requests import perun_rpc

_logger = getLogger(__name__)
__url = "attributesManager"


async def get_attributes(group_id: int) -> List[Any]:
    return await perun_rpc(f"{__url}/getAttributes", params={"group": group_id})


ValueType = TypeVar("ValueType")


class Attribute(Generic[ValueType]):
    id: int
    displayName: str
    description: str
    friendlyName: str
    value: ValueType
    valueModifiedAt: datetime

    # parser/converter functions for the attribute of an Attribute, let's call them
    # subattributes
    _parser_funcs: Dict[str, Callable[[str], Any]] = {
        "valueModifiedAt": lambda value: datetime.strptime(
            value, "%Y-%m-%d %H:%M:%S.%f"
        ),
        "id": int,
    }

    # helper functions to fix shortcomings of the perun api, i.e. no support for floats
    # values with necessary conversions are identified by the friendlyName of the
    # Attribute
    _value_funcs: Dict[str, Callable[[Any], Any]] = {
        # in case some "genius" used the broken german notation with an actual
        # commata
        "denbiCreditsCurrent": lambda value: float(
            value.replace(",", ".") if isinstance(value, str) else float(value)
        ),
        "denbiCreditsGranted": lambda value: float(
            value.replace(",", ".") if isinstance(value, str) else float(value)
        ),
    }

    def __init__(self, **kwargs):
        for attribute_attr_name in __class__.__annotations__:
            # ignore any non public attributes here, such as _parser_funcs
            if attribute_attr_name.startswith("_"):
                continue
            # check whether any parser function is defined and apply it if so
            if attribute_attr_name in __class__._parser_funcs:
                attribute_attr_value = __class__._parser_funcs[attribute_attr_name](
                    kwargs[attribute_attr_name]
                )
            else:
                attribute_attr_value = kwargs[attribute_attr_name]
            self.__setattr__(attribute_attr_name, attribute_attr_value)
        try:
            self.value = __class__._value_funcs[self.friendlyName](self.value)
        except KeyError:
            pass

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        param_repr: List[str] = []
        for attribute in filter(
            lambda attribute: not attribute.startswith("_"), self.__annotations__.keys()
        ):
            param_repr.append(f"{attribute}={repr(self.__getattribute__(attribute))}")

        return f"Attribute({','.join(param_repr)})"
