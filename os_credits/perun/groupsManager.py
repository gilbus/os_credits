"""
Implements the RPC-Calls of the GroupsManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-GroupsManager.html
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Set, Type, cast

from os_credits.log import internal_logger
from os_credits.settings import config

from .attributes import (
    DenbiCreditsCurrent,
    DenbiCreditsGranted,
    DenbiCreditTimestamps,
    PerunAttribute,
    ToEmail,
    registered_attributes,
)
from .attributesManager import (
    get_attributes,
    get_resource_bound_attributes,
    set_attributes,
    set_resource_bound_attributes,
)
from .requests import perun_get
from .resourcesManager import get_assigned_resources

__url = "groupsManager"


async def get_all_groups(
    vo: int = config["OS_CREDITS_PERUN_VO_ID"]
) -> Dict[str, Group]:
    """
    Return all groups in the given VO.

    :return: Dictionary of all groups with their name as index
    """
    all_groups = await perun_get(f"{__url}/getAllGroups", params={"vo": vo})
    return {group["name"]: await Group(group["name"]).connect() for group in all_groups}


async def get_group_by_name(
    name: str, vo: int = config["OS_CREDITS_PERUN_VO_ID"]
) -> Dict[str, Any]:
    """:return: Dictionary of attributes of the requested Group."""
    return cast(
        Dict[str, Any],
        await perun_get(f"{__url}/getGroupByName", params={"vo": vo, "name": name}),
    )


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
    assigned_resource_ids: Set[int]

    email: ToEmail
    credits_granted: DenbiCreditsGranted
    credits_current: DenbiCreditsCurrent
    credits_timestamps: DenbiCreditTimestamps

    """
    Since we process every measurement indenpendently but store the results in the same
    group object inside perun we need to make sure that all transactions are performed
    atomically.
    """

    def __init__(self, name: str, resource_id: int = 0) -> None:
        """
        Calling this method only creates the object, but does not query perun yet. Call
        .connect() which returns the object itself to support method chaining and is
        async.

        :param name: Name of group inside Perun.
        """
        self.name = name
        self.resource_id = resource_id
        self.assigned_resource_ids = set()

    async def connect(self) -> Group:
        group_response = await get_group_by_name(self.name)
        self.id = int(group_response["id"])

        group_attributes = {
            attribute["friendlyName"]: attribute
            for attribute in await get_attributes(self.id)
        }
        internal_logger.debug(
            "Found Group '%s' in Perun and retrived attributes", self.name
        )

        requested_resource_bound_attributes: Set[str] = set()

        for (attr_name, attr_class) in Group._perun_attributes().items():
            # `group_attributes` does not contain any resource-bound attributes
            if attr_class.is_resource_bound():
                requested_resource_bound_attributes.add(attr_name)
            # only save attributes which are requested via class annotations
            attr_friendly_name = attr_class.friendlyName
            try:
                self.__setattr__(
                    attr_name, attr_class(**group_attributes[attr_friendly_name])
                )
            except KeyError:
                self.__setattr__(attr_name, attr_class(value=None))

        if requested_resource_bound_attributes:
            await self._retrieve_resource_bound_attributes(
                requested_resource_bound_attributes
            )

        return self

    async def _retrieve_resource_bound_attributes(
        self, attribute_names: Set[str]
    ) -> None:
        self.assigned_resource_ids = {
            resource["id"] for resource in await get_assigned_resources(self.id)
        }
        if self.resource_id not in self.assigned_resource_ids:
            internal_logger.warning(
                "Group `%s` is not connected with resource with id `%s`. "
                "Skipping retrival of resource bound attributes such as credits_timestamps",
                self.name,
                self.resource_id,
            )
            return
        resource_bound_attributes = {
            attribute["friendlyName"]: attribute
            for attribute in await get_resource_bound_attributes(
                self.id, self.resource_id
            )
        }
        internal_logger.debug(
            "Retrieved resource bound attributes Group %s and Resource %s: %s",
            self.name,
            self.resource_id,
            resource_bound_attributes,
        )
        for attr_name in attribute_names:
            attr_class = Group._perun_attributes()[attr_name]
            try:
                self.__setattr__(
                    attr_name,
                    attr_class(**resource_bound_attributes[attr_class.friendlyName]),
                )
            except KeyError:
                self.__setattr__(attr_name, attr_class(value=None))

    async def save(self) -> None:
        """Save all changed attribute values to Perun."""
        # If this class is shared among multiple coroutines the following approach might
        # not be 'thread-safe' since another class could update the values during the
        # 'await' phase
        internal_logger.debug("Save of Group %s called", self)
        changed_attrs: List[PerunAttribute[Any]] = []
        changed_resource_bound_attrs: List[PerunAttribute[Any]] = []
        for attribute_name in Group._perun_attributes():
            attr = getattr(self, attribute_name)
            if attr.has_changed:
                if not attr.is_resource_bound():
                    changed_attrs.append(attr)
                else:
                    changed_resource_bound_attrs.append(attr)
        if changed_attrs:
            internal_logger.debug(
                "Sending modified regular attributes to perun %s", changed_attrs
            )
            await set_attributes(self.id, changed_attrs)
        if changed_resource_bound_attrs:
            if self.resource_id in self.assigned_resource_ids:
                internal_logger.debug(
                    "Sending modified resource bound attributes to perun %s",
                    changed_attrs,
                )
                await set_resource_bound_attributes(
                    self.id, self.resource_id, changed_resource_bound_attrs
                )
            else:
                internal_logger.warning(
                    "Not sending modified attribute to perun, since Group %s is not "
                    "connected with resource with id %s"
                    "",
                    self,
                    self.resource_id,
                )

    def __repr__(self) -> str:
        # in case Group has not been connected yet
        if not getattr(self, "id", None):
            return f"Group({self.name})"
        param_repr: List[str] = []
        for attribute in Group._perun_attributes():
            param_repr.append(f"{attribute}={repr(self.__getattribute__(attribute))}")

        return f"Group[{','.join(param_repr)}]"

    def __str__(self) -> str:
        return f"{self.name}@{self.resource_id}"

    @classmethod
    async def get_all_groups(
        cls, vo: int = config["OS_CREDITS_PERUN_VO_ID"]
    ) -> Dict[str, Group]:
        """
        Returns all groups in the given VO.
        :return: Dictionary of all groups with their name as index
        """
        return await get_all_groups(vo)

    @staticmethod
    @lru_cache()
    def _perun_attributes() -> Dict[str, Type[PerunAttribute[Any]]]:
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
                internal_logger.debug(
                    "Connected group attribute `%s` with PerunAttribute `%s`",
                    attr_name,
                    attr_class_name,
                )
            except KeyError:
                # this will fail for any non-Perun attribute, such as name or id
                pass
        return attributes
