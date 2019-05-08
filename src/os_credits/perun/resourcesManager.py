"""
Implements the RPC-Calls of the ResourcesManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-ResourcesManager.html
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

from .requests import perun_get

_URL = "resourcesManager"


async def get_assigned_resources(group_id: int) -> List[Dict[str, Any]]:
    """
    https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-ResourcesManager.html#ResourcesManagergetAssignedResources1
    """
    params = {"group": group_id}
    # cast is only for type checking purposes
    return cast(
        List[Dict[str, Any]],
        await perun_get(f"{_URL}/getAssignedResources", params=params),
    )
