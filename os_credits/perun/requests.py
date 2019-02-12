from logging import getLogger
from typing import Any, Dict, Optional

from aiohttp import BasicAuth, ClientSession
from os_credits.exceptions import (
    AttributeNotExistsError,
    ConsistencyError,
    GroupNotExistsError,
    InternalError,
    RequestError,
)
from os_credits.settings import config

_client = ClientSession(
    auth=BasicAuth(config["service_user"]["login"], config["service_user"]["password"])
)
_logger = getLogger(__name__)


async def close_session(_):
    "Close session with grace."
    await _client.close()


async def perun_rpc(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    request_url = f"{config['perun_rpc_base_url']}/{url}"
    _logger.debug("Sending POST request `%s` with data `%s`", request_url, params)
    async with _client.post(request_url, json=params) as response:
        response_content = await response.json()
        if response_content and "errorId" in response_content:
            # Some kind of error has occured
            if response_content["name"] == "GroupNotExistsException":
                raise GroupNotExistsError(response_content["message"])
            elif response_content["name"] == "AttributeNotExistsException":
                raise AttributeNotExistsError(response_content["message"])
            elif response_content["name"] == "InternalErrorException":
                raise InternalError(response_content["message"])
            elif response_content["name"] == "ConsistencyErrorException":
                raise ConsistencyError(response_content["message"])
            else:
                raise RequestError(response_content["message"])

        return response_content
