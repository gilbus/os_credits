"""
Implements the RPC-Calls of the AttributesManager
https://perun-aai.org/documentation/technical-documentation/rpc-api/rpc-javadoc-AttributesManager.html
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List, Optional

from .attributes import PerunAttribute
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


async def set_attribute(group_id: int, attribute: PerunAttribute) -> None:
    await perun_rpc(
        f"{__url}/setAttribute",
        {"group": group_id, "attribute": attribute.to_perun_dict()},
    )
