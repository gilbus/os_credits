"""
Implements the RPC-Calls of the `GroupsManager
<https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-GroupsManager.html>`_.
"""

from __future__ import annotations

from typing import Any, Dict, cast

from os_credits.settings import config

from .requests import perun_get

__url = "groupsManager"


async def get_group_by_name(name: str) -> Dict[str, Any]:
    """Retrieve all information of a Group from *Perun*.

    Name of the function is chosen to match the one from the `Perun documentation
    <https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-GroupsManager.html#GroupsManagergetGroupByName1>`_.

    :param name: Name of the Group/Project whose information should be retrieved.
    :return: Dictionary of attributes of the requested Group."""
    return cast(
        Dict[str, Any],
        await perun_get(
            f"{__url}/getGroupByName",
            params={"vo": config["OS_CREDITS_PERUN_VO_ID"], "name": name},
        ),
    )
