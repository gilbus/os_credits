from __future__ import annotations

from asyncio import Lock, Queue, create_task, gather
from collections import defaultdict
from datetime import datetime
from logging.config import dictConfig
from pathlib import Path
from pprint import pformat
from typing import Optional

from aiohttp import BasicAuth, ClientSession, web
from aiohttp_jinja2 import setup
from aiohttp_swagger import setup_swagger
from jinja2 import FileSystemLoader
from prometheus_async import aio

from os_credits.credits.tasks import worker
from os_credits.exceptions import MissingInfluxDatabase
from os_credits.influx.client import InfluxDBClient
from os_credits.log import internal_logger
from os_credits.perun.requests import client_session
from os_credits.prometheus_metrics import projects_processed_counter, tasks_queued_gauge
from os_credits.views import (
    application_stats,
    costs_per_hour,
    credits_history,
    credits_history_api,
    get_metrics,
    influxdb_write_endpoint,
    ping,
    update_logging_config,
)

APP_ROOT = Path(__file__).parent


async def create_worker(app: web.Application) -> None:
    app["task_workers"] = {
        f"worker-{i}": create_task(worker(f"worker-{i}", app))
        for i in range(app["config"]["OS_CREDITS_WORKERS"])
    }
    internal_logger.info("Created %d workers", len(app["task_workers"]))


async def stop_worker(app: web.Application) -> None:
    for task in app["task_workers"].values():
        task.cancel()
    await gather(*app["task_workers"].values(), return_exceptions=True)


async def create_client_session(app: web.Application) -> None:
    client_session.set(
        ClientSession(
            auth=BasicAuth(
                app["config"]["OS_CREDITS_PERUN_LOGIN"],
                app["config"]["OS_CREDITS_PERUN_PASSWORD"],
            )
        )
    )


async def setup_prometheus_metrics(app: web.Application) -> None:
    tasks_queued_gauge.set_function(lambda: app["task_queue"].qsize())


async def close_client_session(_: web.Application) -> None:
    try:
        await client_session.get().close()
    except LookupError:
        # no session: no need to close a session
        pass


def create_new_group_lock() -> Lock:
    projects_processed_counter.inc()
    return Lock()


async def create_app(
    _existing_influxdb_client: Optional[InfluxDBClient] = None
) -> web.Application:
    """
    Separated from main function to be usable via `python -m aiohttp.web [...]`. Takes
    care of any application related setup, e.g. which config to use.
    """
    # imported inside the function to allow pytest to set environment variables and have
    # them applied
    from os_credits.settings import DEFAULT_LOGGING_CONFIG, config

    dictConfig(DEFAULT_LOGGING_CONFIG)
    internal_logger.info("Applied default logging config")

    app = web.Application()
    app.add_routes(
        [
            web.get(
                "/api/credits_history/{project_name}",
                credits_history_api,
                name="api_credits_history",
            ),
            web.get("/api/metrics", get_metrics, name="get_metrics"),
            web.post("/api/costs_per_hour", costs_per_hour, name="costs_per_hour"),
            web.get(
                "/credits_history/{project_name}",
                credits_history,
                name="credits_history",
            ),
            # not naming this route since it also used as health check by Docker
            web.get("/ping", ping, name="ping"),
            web.get("/stats", application_stats),
            # not naming this route since the endpoint is defined by InfluxDB
            web.post("/write", influxdb_write_endpoint),
            web.post("/logconfig", update_logging_config),
            web.get("/metrics", aio.web.server_stats, name="metrics"),
            web.static("/static", APP_ROOT / "static"),
        ]
    )
    app.update(
        name="os-credits",
        influx_client=_existing_influxdb_client or InfluxDBClient(),
        task_queue=Queue(),
        group_locks=defaultdict(create_new_group_lock),
        start_time=datetime.now(),
        config=config,
    )

    if not await app["influx_client"].ensure_history_db_exists():
        raise MissingInfluxDatabase(
            f"Required database {config['CREDITS_HISTORY_DB']} does not exist inside "
            "InfluxDB. Must be created externally since this code runs without admin "
            "access."
        )

    # setup jinja2 template engine
    setup(app, loader=FileSystemLoader(str(APP_ROOT / "templates")))

    app.on_startup.append(create_client_session)
    app.on_startup.append(create_worker)
    app.on_startup.append(setup_prometheus_metrics)
    app.on_cleanup.append(stop_worker)
    app.on_cleanup.append(close_client_session)

    setup_swagger(app)

    internal_logger.info(
        "Registered resources: %s", pformat(list(app.router.resources()))
    )

    return app
