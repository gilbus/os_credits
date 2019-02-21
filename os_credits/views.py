"""
Contains all view function, the routes are specified inside main.py, django style like.
"""
import logging.config
from datetime import datetime
from json import JSONDecodeError, loads

from aiohttp import web

from os_credits.log import internal_logger


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
        internal_logger.debug(
            "Put influx_line %s into queue (%s)",
            line,
            request.app["task_queue"].qsize(),
        )
    # always return 204, even if we do not know whether the lines are valid
    return web.HTTPNoContent()


async def application_stats(request: web.Request) -> web.Response:
    """
    API-Endpoint returning current stats of the running application
    """
    stats = {
        "number_of_workers": request.app["config"]["application"]["number_of_workers"],
        "queue_size": request.app["task_queue"].qsize(),
        "number_of_locks": len(request.app["group_locks"]),
        "uptime": str(datetime.now() - request.app["start_time"]),
    }
    return web.json_response(stats)


async def update_logging_config(request: web.Request) -> web.Response:
    """
    Possibility to update logging configuration without restart
    """
    logging_json_text = await request.text()
    try:
        logging_config = loads(logging_json_text)
    except JSONDecodeError as e:
        raise web.HTTPBadRequest(reason=str(e))
    try:
        logging.config.dictConfig(logging_config)
    except Exception as e:
        raise web.HTTPBadRequest(reason=str(e))
    raise web.HTTPNoContent()
