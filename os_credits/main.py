from __future__ import annotations

from asyncio import Lock, Queue, gather
from collections import defaultdict
from datetime import datetime
from logging.config import dictConfig

from aiohttp import BasicAuth, ClientSession, web
from os_credits.credits.tasks import worker
from os_credits.influxdb import InfluxClient
from os_credits.log import internal_logger
from os_credits.perun.requests import client_session
from os_credits.settings import config
from os_credits.views import (
    application_stats,
    influxdb_write_endpoint,
    ping,
    update_logging_config,
)

WORKER_NUMBER = config["application"].get("number_of_workers", 10)


async def create_worker(app: web.Application) -> None:
    app["task_workers"] = {
        f"worker-{i}": app.loop.create_task(worker(f"worker-{i}", app))
        for i in range(WORKER_NUMBER)
    }
    internal_logger.info("Created %d workers", WORKER_NUMBER)


async def stop_worker(app: web.Application) -> None:
    for task in app["task_workers"].values():
        task.cancel()
    await gather(*app["task_workers"].values(), return_exceptions=True)


async def create_client_session(_) -> None:
    client_session.set(
        ClientSession(
            auth=BasicAuth(
                config["service_user"]["login"], config["service_user"]["password"]
            )
        )
    )


async def close_client_session(_) -> None:
    await client_session.get().close()


async def create_app() -> web.Application:
    """
    Separated from main function to be usable via `python -m aiohttp.web [...]`. Takes
    care of any application related setup, e.g. which config to use.
    """

    app = web.Application()
    app.add_routes(
        [
            web.get("/ping", ping),
            web.post("/write", influxdb_write_endpoint),
            web.get("/stats", application_stats),
            web.post("/logconfig", update_logging_config),
        ]
    )
    app.update(
        name="os-credits",
        config=config,
        influx_client=InfluxClient(),
        task_queue=Queue(),
        group_locks=defaultdict(Lock),
        start_time=datetime.now(),
    )
    if "logging" in config:
        dictConfig(config["logging"])

    app.on_startup.append(create_client_session)
    app.on_startup.append(create_worker)
    app.on_cleanup.append(stop_worker)
    app.on_cleanup.append(close_client_session)

    return app
