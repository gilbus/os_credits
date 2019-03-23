"""
Implements the RPC-Calls of the AttributesManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-AttributesManager.html
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, cast

from os_credits.settings import config

from .attributes import DenbiCreditsGranted, PerunAttribute
from .requests import perun_get, perun_set

_URL = "attributesManager"

# Used during offline/dummy mode to emulate Perun
_dummy_mode_resource_attributes: Dict[
    Tuple[int, int], Dict[str, Dict[str, Any]]
] = defaultdict(lambda: {})
# Insert any initial values by using a defaultdict
_dummy_mode_group_attributes: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(
    lambda: {
        DenbiCreditsGranted.friendlyName: DenbiCreditsGranted(
            value=config["OS_CREDITS_DUMMY_CREDITS_GRANTED"]
        ).to_perun_dict()
    }
)


async def get_resource_bound_attributes(
    group_id: int,
    resource_id: int,
    attribute_friendly_names: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not config["OS_CREDITS_DUMMY_MODE"]:
        params: Dict[str, Any] = {"group": group_id, "resource": resource_id}
        if attribute_friendly_names:
            params.update({"attrNames": attribute_friendly_names})
        # cast is only for type checking purposes
        return cast(
            List[Dict[str, Any]],
            await perun_get(f"{_URL}/getAttributes", params=params),
        )
    else:
        if attribute_friendly_names:
            return [
                _dummy_mode_resource_attributes[(group_id, resource_id)][friendly_name]
                for friendly_name in attribute_friendly_names
            ]
        else:
            return [
                attribute
                for attribute in _dummy_mode_resource_attributes[
                    (group_id, resource_id)
                ].values()
            ]


async def get_attributes(
    group_id: int, attribute_friendly_names: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    if not config["OS_CREDITS_DUMMY_MODE"]:
        params: Dict[str, Any] = {"group": group_id}
        if attribute_friendly_names:
            params.update({"attrNames": attribute_friendly_names})
        # cast is only for type checking purposes
        return cast(
            List[Dict[str, Any]],
            await perun_get(f"{_URL}/getAttributes", params=params),
        )
    else:
        if attribute_friendly_names:
            return [
                _dummy_mode_group_attributes[group_id][friendly_name]
                for friendly_name in attribute_friendly_names
            ]

        else:
            return [
                attribute
                for attribute in _dummy_mode_group_attributes[group_id].values()
            ]


async def set_attribute(group_id: int, attribute: PerunAttribute[Any]) -> None:
    if not config["OS_CREDITS_DUMMY_MODE"]:
        await perun_set(
            f"{_URL}/setAttribute",
            {"group": group_id, "attribute": attribute.to_perun_dict()},
        )
    else:
        _dummy_mode_group_attributes[group_id][
            attribute.friendlyName
        ] = attribute.to_perun_dict()


async def set_resource_bound_attributes(
    group_id: int, resource_id: int, attributes: List[PerunAttribute[Any]]
) -> None:
    if not config["OS_CREDITS_DUMMY_MODE"]:
        await perun_set(
            f"{_URL}/setAttributes",
            {
                "group": group_id,
                "resource": resource_id,
                "attributes": [attr.to_perun_dict() for attr in attributes],
            },
        )
    else:
        for attribute in attributes:
            _dummy_mode_resource_attributes[(group_id, resource_id)][
                attribute.friendlyName
            ] = attribute.to_perun_dict()


async def set_attributes(group_id: int, attributes: List[PerunAttribute[Any]]) -> None:
    if not config["OS_CREDITS_DUMMY_MODE"]:
        await perun_set(
            f"{_URL}/setAttributes",
            {
                "group": group_id,
                "attributes": [attr.to_perun_dict() for attr in attributes],
            },
        )
    else:
        for attribute in attributes:
            _dummy_mode_group_attributes[group_id][
                attribute.friendlyName
            ] = attribute.to_perun_dict()
