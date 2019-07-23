from argparse import ArgumentDefaultsHelpFormatter
from argparse import ArgumentParser
from os import getenv

from aiohttp import web

from os_credits import __author__
from os_credits import __license__
from os_credits import __version__
from os_credits.log import internal_logger

CONFIG_FILE_ENV_VAR = "CREDITS_SETTINGS_FILE"
PORT_ENV_VAR = "CREDITS_PORT"
HOST_ENV_VAR = "CREDITS_HOST"
UNIX_DOMAIN_SOCKET_ENV_VAR = "CREDITS_UNIX_SOCKET"


def main() -> int:
    parser = ArgumentParser(
        epilog=f"{__license__} @ {__author__} - v{__version__}",
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
    parser.add_argument("--version", action="version", version=__version__)

    args = parser.parse_args()

    try:
        from os_credits.main import create_app

        web.run_app(create_app(), port=args.port, path=args.path, host=args.host)
    except OSError:
        internal_logger.exception(
            "Could not start start application, see stacktrace attached."
        )
        return 1
    except Exception:
        internal_logger.exception("Unhandled exception.")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
