"""
Contains all view function, the routes are specified inside main.py, django style like.
"""
from logging import getLogger

from aiohttp import web
from asyncio import create_task

from .credits import REQUIRED_MEASUREMENTS, process_influx_line
from .influxdb import InfluxClient

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
        create_task(process_influx_line(line, request.app["influx_client"]))
    # always return 204, even if we do not know whether the lines are valid
    return web.HTTPNoContent()
