from __future__ import annotations

import logging
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, FileType
from asyncio import Lock, Queue, gather
from collections import defaultdict
from datetime import datetime
from logging.config import dictConfig
from os import getenv

from aiohttp import BasicAuth, ClientSession, web

from os_credits.credits.tasks import worker
from os_credits.influxdb import InfluxClient
from os_credits.log import internal_logger
from os_credits.perun.requests import client_session
from os_credits.settings import config, default_config_path
from os_credits.views import application_stats, influxdb_write_endpoint, ping

__author__ = "gilbus"
__license__ = "AGPLv3"

CONFIG_FILE_ENV_VAR = "CREDITS_SETTINGS_FILE"
PORT_ENV_VAR = "CREDITS_PORT"
HOST_ENV_VAR = "CREDITS_HOST"
UNIX_DOMAIN_SOCKET_ENV_VAR = "CREDITS_UNIX_SOCKET"

WORKER_NUMBER = config["application"].get("number_of_workers", 10)


def setup_app_internals_parser(parser: ArgumentParser) -> ArgumentParser:
    return parser


async def create_worker(app: web.Application) -> None:
    app["task_workers"] = [
        app.loop.create_task(worker(f"worker-{i}", app)) for i in range(WORKER_NUMBER)
    ]
    internal_logger.info("Created %d workers", WORKER_NUMBER)


async def stop_worker(app: web.Application) -> None:
    for task in app["task_workers"]:
        task.cancel()
    await gather(*app["task_workers"], return_exceptions=True)


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


def main() -> int:
    parser = ArgumentParser(
        epilog=f"{__author__} @ {__license__}",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=getenv(PORT_ENV_VAR, 8080),
        help=f"""TCP/IP port (plain HTTP). Use a reverse proxy for HTTPS. Can also be
        specified via ${PORT_ENV_VAR}""",
    )
    host_args = parser.add_mutually_exclusive_group()
    host_args.add_argument(
        "--host",
        type=str,
        default=getenv(HOST_ENV_VAR, "0.0.0.0"),  # nosec
        help=f"""TCP/IP host. Can also be specified via ${HOST_ENV_VAR}""",
    )
    host_args.add_argument(
        "--path",
        type=str,
        default=getenv(UNIX_DOMAIN_SOCKET_ENV_VAR, None),
        help="""""",
    )
    parser.add_argument("-c", "--config", type=FileType(), default=default_config_path)

    args = parser.parse_args()

    try:
        web.run_app(create_app(), port=args.port, path=args.path, host=args.host)
    except OSError:
        logging.exception("Could not start start application, see stacktrace attached.")
    except Exception:
        logging.exception("Unhandled exception.")

    return 0


if __name__ == "__main__":
    exit(main())
