from __future__ import annotations

from typing import Optional, List, TextIO, Dict
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, FileType
from logging import getLogger
from logging.config import dictConfig
from os import getenv
from asyncio import Queue, gather, Lock
from collections import defaultdict

from aiohttp import web

from os_credits.views import ping, influxdb_write_endpoint
from os_credits.settings import default_config_path, load_config, config
from os_credits.perun.requests import close_session
from os_credits.perun.groupsManager import Group
from os_credits.influxdb import InfluxClient
from os_credits.credits.tasks import worker

__author__ = "gilbus"
__license__ = "AGPLv3"

CONFIG_FILE_ENV_VAR = "CREDITS_SETTINGS_FILE"
PORT_ENV_VAR = "CREDITS_PORT"
HOST_ENV_VAR = "CREDITS_HOST"
UNIX_DOMAIN_SOCKET_ENV_VAR = "CREDITS_UNIX_SOCKET"

WORKER_NUMBER = 4

_logger = getLogger(__name__)
_group_locks: Dict[Group, Lock] = defaultdict(Lock)


def setup_app_internals_parser(parser: ArgumentParser) -> ArgumentParser:
    return parser


async def create_worker(app: web.Application) -> None:
    app["task_workers"] = [
        app.loop.create_task(
            worker(f"worker-{i}", app["task_queue"], app, _group_locks)
        )
        for i in range(WORKER_NUMBER)
    ]


async def stop_worker(app: web.Application) -> None:
    for task in app["task_workers"]:
        task.cancel()
    await gather(*app["task_workers"], return_exceptions=True)


async def create_app() -> web.Application:
    """
    Separated from main function to be usable via `python -m aiohttp.web [...]`. Takes
    care of any application related setup, e.g. which config to use.
    """

    app = web.Application()
    app.add_routes(
        [web.get(r"/ping", ping), web.post("/write", influxdb_write_endpoint)]
    )
    task_queue = Queue()
    app.update(
        name="os-credits",
        config=config,
        influx_client=InfluxClient(),
        task_queue=task_queue,
    )
    if "logging" in config:
        dictConfig(config["logging"])

    app.on_shutdown.append(close_session)
    app.on_shutdown.append(stop_worker)
    app.on_startup.append(create_worker)

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
        default=getenv(HOST_ENV_VAR, "0.0.0.0"),
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

    _logger = getLogger(__name__)
    _logger.debug(args)

    try:
        web.run_app(create_app(), port=args.port, path=args.path, host=args.host)
    except OSError as e:
        _logger.exception("Could not start start application, see stacktrace attached.")
    except Exception:
        _logger.exception("Unhandled exception.")

    return 0


if __name__ == "__main__":
    exit(main())
