from typing import Optional, Any, Dict
from aiohttp import ClientSession, BasicAuth

from .exceptions import GroupNotExistsException
from .. import SERVICE_USER_LOGIN, SERVICE_USER_PASSWORD, PERUN_RPC_BASE_URL

_client = ClientSession(auth=BasicAuth(SERVICE_USER_LOGIN, SERVICE_USER_PASSWORD))


async def perun_rpc(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    async with _client.post(f"{PERUN_RPC_BASE_URL}/{url}", json=params) as response:
        response_content = await response.json()
        if "errorId" in response_content:
            # Some kind of error has occured
            if response_content["name"] == "GroupNotExistsException":
                raise GroupNotExistsException(response_content["message"])
        return response_content
