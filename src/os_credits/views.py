"""
Contains all view function, the routes are specified inside main.py, django style like.
"""
import logging.config
from datetime import datetime
from decimal import Decimal
from json import JSONDecodeError, loads
from traceback import format_stack
from typing import Any, Dict, List, Union

from aiohttp import web
from aiohttp_jinja2 import template

from os_credits.credits.base_models import Metric
from os_credits.influx.client import InfluxDBClient
from os_credits.log import internal_logger
from os_credits.settings import config


async def ping(_: web.Request) -> web.Response:
    """
    Simple ping endpoint to be able to determine whether the application is up and
    running.
    ---
    description: This end-point allow to test that service is up.
    tags:
    - Health check
    produces:
    - text/plain
    responses:
        "200":
            description: successful operation. Return "pong" text
        "405":
            description: invalid HTTP Method
    """
    return web.Response(text="Pong")


async def credits_history_api(request: web.Request) -> web.Response:
    project_name = request.match_info["project_name"]
    influx_client: InfluxDBClient = request.app["influx_client"]
    time_column = ["timestamps"]
    credits_column: List[Union[str, float]] = ["credits"]
    metric_column = ["metrics"]
    async for point in await influx_client.query_billing_history(
        project_name, since=datetime(2019, 4, 19)
    ):
        time_column.append(point.time.strftime("%Y-%m-%d %H:%M:%S"))
        credits_column.append(float(point.credits_left))
        metric_column.append(point.metric_friendly_name)
    return web.json_response(
        {"timestamps": time_column, "credits": credits_column, "metrics": metric_column}
    )


@template("credits_history.html.j2")
async def credits_history(request: web.Request) -> Dict[str, Any]:
    return {"project_name": request.match_info["project_name"]}


async def influxdb_write_endpoint(request: web.Request) -> web.Response:
    """
    Consumes the Line Protocol of InfluxDB, see
    https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_tutorial/
    ---
    description: Used by InfluxDB to post subscription updates
    tags:
      - Service
    consumes:
      - text/plain
    parameters:
      - in: body
        name: line
        description: Point in [`Line Protocol format`](https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_tutorial)
        schema:
          type: string
          example: weather,location=us-midwest temperature=82 1465839830100400200
        required: true
    responses:
      202:
        description: A corresponding task object will be created. See application log
          for further information
      400:
        description: Empty content provided
    """
    # .text() performs automatic decoding from bytes
    influxdb_lines = await request.text()
    # an unknown number of lines will be send, create separate tasks for all of them
    for influx_line in influxdb_lines.splitlines():
        await request.app["task_queue"].put(influx_line)
        internal_logger.debug(
            "Put %s into queue (%s elements)",
            influx_line,
            request.app["task_queue"].qsize(),
        )
    # always answer 202, even if some lines may be invalid/not needed
    return web.HTTPAccepted()


async def application_stats(request: web.Request) -> web.Response:
    """
    API-Endpoint returning current stats of the running application
    ---
    description: Allows querying the application state. Should not be public accessible.
    tags:
      - Health check
      - Monitoring
    produces:
      - application/json
    parameters:
      - in: query
        name: verbose
        type: boolean
        default: false
        description: Include extended (computationally expensive) information
    responses:
      200:
        description: Stats object
        schema:
          type: object
          required: [number_of_workers, queue_size, number_of_locks, uptime]
          properties:
            number_of_workers:
              type: integer
              description: Number of worker tasks as specified in config file
            queue_size:
              type: integer
              description: Number of tasks currently pending
            number_of_locks:
              type: integer
              description: Number of group/project locks inside the application, should
                correspond to the number of billed/groups/projects
            uptime:
              type: string
              description: Uptime, string representation of a python [`timedelta`](https://docs.python.org/3/library/datetime.html#timedelta-objects)
                object
            task_stacks:
              type: object
              required: [worker-n]
              properties:
                worker-n:
                  type: str
                  description: Stack of the worker task
            group_locks:
              type: object
              required: [group_name]
              properties:
                group_name:
                  type: str
                  description: State of the group/project async-lock
    """
    stats = {
        "number_of_workers": config["OS_CREDITS_WORKERS"],
        "queue_size": request.app["task_queue"].qsize(),
        "number_of_locks": len(request.app["group_locks"]),
        "uptime": str(datetime.now() - request.app["start_time"]),
    }
    if (
        "verbose" in request.query
        and request.query["verbose"]
        and request.query["verbose"] != "false"
    ):
        stats.update(
            {
                "task_stacks": {
                    name: [format_stack(stack)[0] for stack in task.get_stack()][0]
                    for name, task in request.app["task_workers"].items()
                },
                "group_locks": {
                    key: repr(lock) for key, lock in request.app["group_locks"].items()
                },
            }
        )
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


# Usage of class-based views would be nicer, unfortunately not yet supported by
# aiohttp-swagger
async def get_credits_measurements(_: web.Request) -> web.Response:
    """
    Returns a JSON object describing the currently supported measurements and
    therefore the supported values when interested in the potential per-hour usage of
    given machines.
    ---
    description: Get type and description of currently needed/supported measurements.
      Also describes the structure of the corresponding POST API to calculate the per
      hour-usage of a given machine constellation.
    tags:
      - Service
    produces:
      - application/json
    responses:
      200:
        description: Information object
        schema:
          type: object
          required: [measurements]
          properties:
            measurements:
              type: object
              required: [description, type, prometheus_name]
              properties:
                description:
                  type: str
                  description: Description of the measurement
                type:
                  type: str
                  description: Type information
                prometheus_name:
                  type: str
                  description: Name/Identifier of the metric inside prometheus and InfluxDB
    """
    measurement_information = {
        friendly_name: measurement.api_information()
        for friendly_name, measurement in Metric.friendly_name_to_usage().items()
    }
    return web.json_response(measurement_information)


async def costs_per_hour(request: web.Request) -> web.Response:
    """
    ---
    description: Given the submitted specs of one or multiple machines combined
      calculate the expected costs per hour. See the corresponding GET API to retrieve
      information about the supported specs.
    tags:
      - Service
    consumes:
      - application/json
    produces:
      - application/json
    responses:
      200:
        description: Costs per hour
        schema:
          type: float
    """
    try:
        machine_specs = await request.json()
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason="Invalid JSON")
    costs_per_hour = Decimal(0)
    for friendly_name, spec in machine_specs.items():
        try:
            costs_per_hour += Metric.friendly_name_to_usage()[
                friendly_name
            ].costs_per_hour(spec)
        except KeyError:
            raise web.HTTPNotFound(reason=f"Unknown measurement `{friendly_name}`.")
        except TypeError:
            raise web.HTTPBadRequest(
                reason=f"Parameter {friendly_name} had wrong type."
            )
    return web.json_response(
        float(costs_per_hour.quantize(config["OS_CREDITS_PRECISION"]))
    )
