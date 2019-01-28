from __future__ import annotations

from typing import Optional, List, TextIO
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, FileType
from logging import getLogger
from os import getenv

from aiohttp import web

from .views import hello
from .settings import default_config_path, load_config, config
from .perun.requests import close_session

__author__ = "gilbus"
__license__ = "AGPLv3"

CONFIG_FILE_ENV_VAR = "CREDITS_SETTINGS_FILE"
PORT_ENV_VAR = "CREDITS_PORT"
HOST_ENV_VAR = "CREDITS_HOST"
UNIX_DOMAIN_SOCKET_ENV_VAR = "CREDITS_UNIX_SOCKET"


def setup_app_internals_parser(parser: ArgumentParser) -> ArgumentParser:
    return parser


def app_init(
    argv=None, config_path: str = getenv(CONFIG_FILE_ENV_VAR, str(default_config_path))
) -> web.Application:
    """
    Separated from main function to be usable via `python -m aiohttp.web [...]`. Takes
    care of any application related setup, e.g. which config to use.
    """

    app = web.Application()
    with open(config_path) as file:
        app["config"] = load_config(file)
    app.add_routes([web.get(r"/{id}", hello)])

    app.on_shutdown.append(close_session)

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
    print(args)

    _logger = getLogger(__name__)

    try:
        web.run_app(
            app_init(args.config), port=args.port, path=args.path, host=args.host
        )
    except OSError as e:
        _logger.exception("Could not start start application, see stacktrace attached.")
    except Exception:
        _logger.exception("Unhandled exception.")

    return 0


if __name__ == "__main__":
    exit(main())
