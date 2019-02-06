"""
Implements the RPC-Calls of the GroupsManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-GroupsManager.html
"""

from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, Callable, List, Optional, Type, Set
from datetime import datetime
from collections import defaultdict
from re import match

from ..settings import config
from .requests import perun_rpc
from . import attributesManager
from .attributesManager import get_attributes, set_attribute
from .attributes import PerunAttribute

_logger = getLogger(__name__)
__url = "groupsManager"


async def get_all_groups(vo: int = config["vo_id"]) -> Dict[str, Group]:
    """
    Return all groups in the given VO.

    :return: Dictionary of all groups with their name as index
    """
    all_groups = await perun_rpc(f"{__url}/getAllGroups", params={"vo": vo})
    return {group["name"]: await Group(group["name"]).connect() for group in all_groups}


async def get_group_by_name(name: str, vo: int = config["vo_id"]) -> Dict[str, Any]:
    """:return: Dictionary of attributes of the requested Group."""
    return await perun_rpc(f"{__url}/getGroupByName", params={"vo": vo, "name": name})


class Group:
    """
    Represents a Group object inside Perun.

    Every attribute requested via class variable declaration will at least be set to
    None in case Perun reports no value. Although the 'inner' type hints are not
    functional (in terms of type checking via `mypy` they are still helpful and
    required, see the regular expressio inside __init__)
    """

    id: int
    name: str
    # list the friendlyName of every attribute to save here
    # the type inside its brackets will be set as type hint for its 'value', the actual
    # value of an attribute
    # please stick to given syntax of annotations since they are also used to list all
    # attributes of a group
    toEmail: PerunAttribute[List[str]]
    denbiCreditsGranted: PerunAttribute[int]
    denbiCreditsCurrent: PerunAttribute[float]
    denbiCreditsTimestamp: PerunAttribute[datetime]

    def __init__(self, name: str) -> None:
        """
        Calling this method only creates the object, but does not query perun yet. Call
        .connect() which returns the object itself to support method chaining and is
        async.
        """
        self.name = name
        self._attribute_types: Dict[str, str] = {}
        for var_name, var_annotation in self.__annotations__.items():
            #
            attribute_match = match(
                r"PerunAttribute\[(?P<value_type>.*)\]", var_annotation
            )
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

        for (
            attr_friendly_name,
            attr_class,
        ) in PerunAttribute._registered_attributes.items():
            # only save attributes which are requested via class annotations
            if attr_friendly_name not in self._attribute_types:
                continue
            try:
                self.__setattr__(
                    attr_friendly_name,
                    attr_class(group=self, **group_attributes[attr_friendly_name]),
                )
            except KeyError:
                self.__setattr__(attr_friendly_name, attr_class(group=self, value=None))

        _logger.debug("Found Group '%s' in Perun and retrived attributes", self.name)

        return self

    async def save(self) -> None:
        """Save all changed attribute values to Perun."""
        # If this class is shared among multiple coroutines the following approach might
        # not be 'thread-safe' since another class could update the values during the
        # 'await' phase
        for attribute_name in self._attribute_types:
            if getattr(self, attribute_name)._updated:
                getattr(self, attribute_name)._updated = False
                await set_attribute(self.id, getattr(self, attribute_name))

    def __repr__(self) -> str:
        param_repr: List[str] = []
        for attribute in self._attribute_types:
            param_repr.append(f"{attribute}={repr(self.__getattribute__(attribute))}")

        return f"Group[{','.join(param_repr)}]"

    def __str__(self) -> str:
        return self.name

    @classmethod
    async def get_all_groups(cls, vo: int = config["vo_id"]) -> Dict[str, Group]:
        """
        Returns all groups in the given VO.
        :return: Dictionary of all groups with their name as index
        """
        return await get_all_groups(vo)
