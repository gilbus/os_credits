"""
Implements the RPC-Calls of the GroupsManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-GroupsManager.html
"""

from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, Callable, List, Optional, Type
from datetime import datetime
from collections import defaultdict
from re import match

from ..settings import config
from .requests import perun_rpc
from .attributesManager import Attribute, get_attributes

_logger = getLogger(__name__)
__url = "groupsManager"


async def get_all_groups(vo: int = config["vo_id"]) -> Dict[str, Group]:
    """
    Returns all groups in the given VO.
    :return: Dictionary of all groups with their name as index
    """
    all_groups = await perun_rpc(f"{__url}/getAllGroups", params={"vo": vo})
    return {group["name"]: await Group(group["name"]).connect() for group in all_groups}


async def get_group_by_name(name: str, vo: int = config["vo_id"]) -> Dict[str, Any]:
    """
    :return: Dictionary of attributes of the requested Group.
    """
    return await perun_rpc(f"{__url}/getGroupByName", params={"vo": vo, "name": name})


class Group:
    """
    Represents a Group object inside Perun. Every attribute requested via class variable
    declaration will at least be set to None in case Perun reports no value.
    """

    id: int
    name: str
    # list the friendlyName of every attribute to save here
    # the type inside its brackets will be set as type hint for its 'value', the actual
    # value of an attribute
    denbiProjectShortname: Attribute[str]
    denbiProjectDescription: Attribute[Optional[str]]
    toEmail: Attribute[List[str]]
    denbiCreditsGranted: Attribute[float]
    denbiCreditsCurrent: Attribute[float]
    denbiCreditsTimestamp: Attribute[datetime]

    def __init__(self, name: str) -> None:
        """
        Calling this method only creates the object, but does not query perun yet. Call
        .connect() which returns the object itself to support method chaining and is
        async.
        """
        self.name = name
        self._attribute_types: Dict[str, str] = {}
        for var_name, var_annotation in self.__annotations__.items():
            attribute_match = match(r"Attribute\[(?P<value_type>.*)\]", var_annotation)
            if attribute_match:
                self._attribute_types.update(
                    {var_name: attribute_match.groupdict()["value_type"]}
                )

        _logger.debug("Created Group %s", name)

    async def connect(self) -> Group:

        group_response = await get_group_by_name(self.name)
        self.id = int(group_response["id"])

        group_attributes = {
            attribute["friendlyName"]: attribute
            for attribute in await get_attributes(self.id)
        }

        for attribute_name, attribute_type in self._attribute_types.items():
            if attribute_name in group_attributes:
                self.__setattr__(
                    attribute_name,
                    Attribute[Type[attribute_type]](**group_attributes[attribute_name]),
                )
            else:
                self.__setattr__(attribute_name, None)

        # for attribute in group_attributes:
        #    # check whether this attribute should be added to the group object, in which
        #    # case its type hint should be 'Attribute[<ValueType>]'
        #    attribute_match = match(
        #        r"Attribute\[(?P<value_type>.*)\]",
        #        self.__annotations__.get(attribute["friendlyName"], ""),
        #    )
        #    if attribute_match:
        #        self.__setattr__(
        #            attribute["friendlyName"],
        #            Attribute[attribute_match.groupdict()["value_type"]](**attribute),
        #        )

        #    # TODO: set all attributes without value to None

        return self

    def __repr__(self) -> str:
        return f"Group(name={self.name})"

    @classmethod
    async def get_all_groups(cls, vo: int = config["vo_id"]) -> Dict[str, Group]:
        """
        Returns all groups in the given VO.
        :return: Dictionary of all groups with their name as index
        """
        return await get_all_groups(vo)
