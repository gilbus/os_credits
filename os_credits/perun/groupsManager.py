"""
Implements the RPC-Calls of the GroupsManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-GroupsManager.html
"""

from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, Callable, List, Optional, Type, Set
from datetime import datetime
from collections import defaultdict
from functools import lru_cache
from asyncio import Lock

from os_credits.settings import config
from .requests import perun_rpc
from .attributesManager import get_attributes, set_attribute
from .attributes import (
    PerunAttribute,
    registered_attributes,
    DenbiCreditsTimestamps,
    DenbiCreditsCurrent,
    DenbiCreditsGranted,
    ToEmail,
)

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

    Every attribute requested via class variable annotations, where the annotation
    is a subclass of PerunAttribute, will be set on the class with the chosen name. This
    happens during `connect()` which tries to fill the Attributes with information from
    Perun.
    """

    id: int
    name: str

    email: ToEmail
    credits_granted: DenbiCreditsGranted
    credits_current: DenbiCreditsCurrent
    credits_timestamps: DenbiCreditsTimestamps

    """
    Since we process every measurement indenpendently but store the results in the same
    group object inside perun we need to make sure that all transactions are performed
    atomically.
    """
    _async_locks: Dict[Group, Lock] = {}

    def __init__(self, name: str) -> None:
        """
        Calling this method only creates the object, but does not query perun yet. Call
        .connect() which returns the object itself to support method chaining and is
        async.
        """
        self.name = name
        _logger.debug("Created Group %s", name)
        if self not in Group._async_locks:
            Group._async_locks[self] = Lock()

    async def connect(self) -> Group:

        group_response = await get_group_by_name(self.name)
        self.id = int(group_response["id"])

        group_attributes = {
            attribute["friendlyName"]: attribute
            for attribute in await get_attributes(self.id)
        }

        for (attr_name, attr_class) in Group._perun_attributes().items():
            # only save attributes which are requested via class annotations
            attr_friendly_name = attr_class.friendlyName
            try:
                self.__setattr__(
                    attr_name, attr_class(**group_attributes[attr_friendly_name])
                )
            except KeyError:
                self.__setattr__(attr_name, attr_class(value=None))

        _logger.debug("Found Group '%s' in Perun and retrived attributes", self.name)

        return self

    @property
    def async_lock(self) -> Lock:
        return Group._async_locks[self]

    async def save(self) -> None:
        """Save all changed attribute values to Perun."""
        # If this class is shared among multiple coroutines the following approach might
        # not be 'thread-safe' since another class could update the values during the
        # 'await' phase
        _logger.debug("Save of Group %s called", self)
        for attribute_name in Group._perun_attributes():
            if getattr(self, attribute_name).has_changed:
                _logger.debug(
                    "Attribute %s of Group %s has changed since construction "
                    "Sending new values to perun.",
                    attribute_name,
                    self,
                )
                getattr(self, attribute_name).has_changed = False
                await set_attribute(self.id, getattr(self, attribute_name))

    def __hash__(self) -> int:
        """Override since groups are only identified by their name."""
        return hash((self.name))

    def __repr__(self) -> str:
        param_repr: List[str] = []
        for attribute in Group._perun_attributes():
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

    @staticmethod
    @lru_cache()
    def _perun_attributes() -> Dict[str, Type[PerunAttribute]]:
        """
        Return all Group-attributes which are Perun-Attributes.

        Declaring it as staticmethod and using a lru_cache saves time since the mapping
        only needs to be done once, changes during Runtime would be way to silly.

        :return: Dictionary of the attribute names of a Group and the corresponding
        PerunAttribute subclass.
        """
        attributes = {}
        for attr_name, attr_class_name in Group.__annotations__.items():
            try:
                attributes.update({attr_name: registered_attributes[attr_class_name]})
                _logger.debug(
                    "Connected group attribute `%s` with PerunAttribute `%s`",
                    attr_name,
                    attr_class_name,
                )
            except KeyError:
                # this will fail for any non-Perun attribute, such as name or id
                pass
        return attributes
