"""
Contains all view function, the routes are specified inside main.py, django style like.
"""
from logging import getLogger

from aiohttp import web

_logger = getLogger(__name__)


async def ping(_) -> web.Response:
    """
    Simple ping endpoint to be able to determine whether the application is up and
    running.
    """
    return web.Response(text="Pong")


async def influxdb_write_endpoint(request: web.Request) -> web.Response:
    """
    Consumes the Line Protocol of InfluxDB, see
    https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_tutorial/
    """
    # .text() performs automatic decoding from bytes
    influxdb_lines = await request.text()
    # an unknown number of lines will be send, create separate tasks for all of them
    for line in influxdb_lines.splitlines():
        await request.app["task_queue"].put(line)
    # always return 204, even if we do not know whether the lines are valid
    return web.HTTPNoContent()
