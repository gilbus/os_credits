"""
Implements the RPC-Calls of the GroupsManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-GroupsManager.html
"""

from __future__ import annotations

from logging import getLogger
from typing import Dict, Any, TypeVar, Generic, Callable, List, Optional
from datetime import datetime

from .requests import perun_rpc

_logger = getLogger(__name__)
__url = "attributesManager"

PERUN_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


async def get_attributes(
    group_id: int, attr_names: Optional[List[str]] = None
) -> List[Any]:
    params: Dict[str, Any] = {"group": group_id}
    if attr_names:
        params.update({"attrNames": attr_names})
    return await perun_rpc(f"{__url}/getAttributes", params=params)


async def set_attribute(group_id: int, attribute: Attribute) -> None:
    await perun_rpc(
        f"{__url}/setAttribute",
        {"group": group_id, "attribute": attribute.to_perun_dict()},
    )


ValueType = TypeVar("ValueType")


class Attribute(Generic[ValueType]):
    id: int
    displayName: str
    description: str
    friendlyName: str
    writable: bool
    type: str
    _value: ValueType
    valueModifiedAt: datetime
    namespace: str

    # decoder functions for the subattribute of an Attribute
    _subattr_decoder: Dict[str, Callable[[str], Any]] = {
        "valueModifiedAt": lambda value: datetime.strptime(
            value, PERUN_DATETIME_FORMAT
        ),
        "id": int,
    }

    _subattr_encoder: Dict[str, Callable[[Any], Any]] = {
        "valueModifiedAt": lambda value: value.strftime(PERUN_DATETIME_FORMAT),
        "id": str,
    }

    # helper functions to fix shortcomings of the perun api, i.e. no support for floats
    # values with necessary conversions are identified by the friendlyName of the
    # Attribute
    _value_decoder: Dict[str, Callable[[Any], Any]] = {
        # in case some "genius" used the broken german notation with an actual
        # commata
        "denbiCreditsCurrent": lambda value: float(
            value.replace(",", ".") if isinstance(value, str) else float(value)
        ),
        "denbiCreditsGranted": lambda value: float(
            value.replace(",", ".") if isinstance(value, str) else float(value)
        ),
        "denbiCreditsTimestamp": lambda value: datetime.strptime(
            value, PERUN_DATETIME_FORMAT
        ),
    }
    _value_encoder: Dict[str, Callable[[Any], Any]] = {
        # in case some "genius" used the broken german notation with an actual
        # commata
        "denbiCreditsCurrent": str,
        "denbiCreditsGranted": str,
        "denbiCreditsTimestamp": lambda value: value.strftime(PERUN_DATETIME_FORMAT),
    }

    def __init__(self, **kwargs):
        for attribute_attr_name in __class__.__annotations__:
            # ignore any non public attributes here, such as _parser_funcs
            if attribute_attr_name.startswith("_"):
                continue
            # check whether any parser function is defined and apply it if so
            if attribute_attr_name in __class__._subattr_decoder:
                attribute_attr_value = __class__._subattr_decoder[attribute_attr_name](
                    kwargs[attribute_attr_name]
                )
            else:
                attribute_attr_value = kwargs[attribute_attr_name]
            self.__setattr__(attribute_attr_name, attribute_attr_value)
        try:
            self._value = __class__._value_decoder[self.friendlyName](kwargs["value"])
        except KeyError:
            self._value = kwargs["value"]

    def to_perun_dict(self) -> Dict[str, Any]:
        """Serialize the attribute into a dictionary which can passed as JSON content to
        the perun API"""
        data: Dict[str, Any] = {}
        for attribute_attr_name in self.__annotations__:
            # ignore any non public attributes here, such as _parser_funcs
            if attribute_attr_name.startswith("_"):
                continue
            # check whether any parser function is defined and apply it if so
            if attribute_attr_name in self._subattr_encoder:
                attribute_attr_value = self._subattr_encoder[attribute_attr_name](
                    getattr(self, attribute_attr_name)
                )
            else:
                attribute_attr_value = getattr(self, attribute_attr_name)
            data.update({attribute_attr_name: attribute_attr_value})
        try:
            data["value"] = self._value_encoder[self.friendlyName](self.value)
        except KeyError:
            data["value"] = self.value

        return data

    @property
    def value(self) -> ValueType:
        return self._value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        param_repr: List[str] = [f"value={self.value}"]
        for attribute in filter(
            lambda attribute: not attribute.startswith("_"), self.__annotations__.keys()
        ):
            param_repr.append(f"{attribute}={repr(self.__getattribute__(attribute))}")

        return f"Attribute({','.join(param_repr)})"
