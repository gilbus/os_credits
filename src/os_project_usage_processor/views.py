from logging import getLogger

from aiohttp import web

from .perun import groupsManager
from .perun.requests import GroupNotExistsError

_logger = getLogger(__name__)


async def hello(request: web.Request):
    try:
        group = await groupsManager.Group(request.match_info["id"]).connect()
        return web.Response(text=f"{group}")
    except GroupNotExistsError as e:
        _logger.debug(
            "Group %s not found. Perun message: `%s`", request.match_info["id"], e
        )
        raise web.HTTPNotFound()
