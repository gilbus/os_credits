from __future__ import annotations

from collections import defaultdict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from os_credits.perun.attributes import DenbiCreditsGranted
from os_credits.perun.base_attributes import PerunAttribute

from .conftest import TEST_INITIAL_CREDITS_GRANTED


# replaces `os_credits.perun.groupsManager.get_group_by_name`
async def get_group_by_name(name: str) -> Dict[str, Any]:
    # create fake 8 digit id from name, must not be random since used as key in
    # _test_mode_group_attributes
    group_id = abs(hash(name) % (10 ** 8))
    return {
        "id": group_id,
        "createdAt": "2000-01-01 00:00:00.000000",
        "createdBy": "unknown@example.com",
        "modifiedAt": "2000-01-01 00:00:00.000000",
        "modifiedBy": "unknown@example.com",
        "createdByUid": 0,
        "modifiedByUid": 0,
        "voId": 0,
        "parentGroupId": None,
        "name": name,
        "description": f"Dummy offline group ({group_id})",
        "shortName": name,
        "beanName": "Group",
    }


# Used during test runs to emulate Perun's storage capabilities
_test_mode_resource_attributes: Dict[
    Tuple[int, int], Dict[str, Dict[str, Any]]
] = defaultdict(lambda: {})
# Insert any initial values by using a defaultdict
_test_mode_group_attributes: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(
    lambda: {
        DenbiCreditsGranted.get_full_name(): DenbiCreditsGranted(
            value=TEST_INITIAL_CREDITS_GRANTED
        ).to_perun_dict()
    }
)


# replaces `os_credits.perun.attributesManager.get_resource_bound_attributes`
async def get_resource_bound_attributes(
    group_id: int, resource_id: int, attribute_full_names: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    return [
        attribute
        for attribute in _test_mode_resource_attributes[
            (group_id, resource_id)
        ].values()
    ]


async def get_attributes(
    group_id: int, attribute_full_names: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    return [attribute for attribute in _test_mode_group_attributes[group_id].values()]


async def is_assigned_resource(self) -> bool:
    """
    """
    return True


# Original function currently not in use
async def set_attribute(group_id: int, attribute: PerunAttribute[Any]) -> None:
    _test_mode_group_attributes[group_id][
        attribute.friendlyName
    ] = attribute.to_perun_dict()


async def set_resource_bound_attributes(
    group_id: int, resource_id: int, attributes: List[PerunAttribute[Any]]
) -> None:
    for attribute in attributes:
        _test_mode_resource_attributes[(group_id, resource_id)][
            attribute.friendlyName
        ] = attribute.to_perun_dict()


async def set_attributes(group_id: int, attributes: List[PerunAttribute[Any]]) -> None:
    for attribute in attributes:
        _test_mode_group_attributes[group_id][
            attribute.friendlyName
        ] = attribute.to_perun_dict()
