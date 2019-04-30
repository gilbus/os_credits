from __future__ import annotations

from collections import ChainMap, UserDict
from decimal import Decimal
from os import environ
from typing import Any, Dict, Optional, Set, cast

from mypy_extensions import TypedDict

from os_credits.exceptions import MissingConfigError
from os_credits.log import internal_logger


class Config(TypedDict):
    """Used to keep track of all available settings and allows the type checker to infer
    the types of individual keys.
    """

    OS_CREDITS_PERUN_LOGIN: str
    OS_CREDITS_PERUN_PASSWORD: str
    OS_CREDITS_PERUN_VO_ID: int
    OS_CREDITS_WORKERS: int
    OS_CREDITS_PRECISION: Decimal
    OS_CREDITS_PROJECT_WHITELIST: Optional[Set[str]]
    INFLUXDB_PORT: int
    INFLUXDB_HOST: str
    INFLUXDB_USER: str
    INFLUXDB_USER_PASSWORD: str
    INFLUXDB_DB: str
    CREDITS_HISTORY_DB: str
    MAIL_FROM: str
    MAIL_SMTP_SERVER: str
    MAIL_SMTP_PORT: int
    MAIL_SMTP_USER: str
    MAIL_SMTP_PASSWORD: str
    MAIL_NOT_STARTTLS: bool
    CLOUD_GOVERNANCE_MAIL: str
    """
    If this setting contains a non-empty value all notifications are exclusively sent to
    it.
    """
    NOTIFICATION_TO_OVERWRITE: str


default_config = Config(
    OS_CREDITS_PERUN_LOGIN="",
    OS_CREDITS_PERUN_PASSWORD="",
    OS_CREDITS_PERUN_VO_ID=0,
    OS_CREDITS_WORKERS=10,
    # see python docs for Decimal
    OS_CREDITS_PRECISION=Decimal(10) ** -2,
    OS_CREDITS_PROJECT_WHITELIST=None,
    INFLUXDB_PORT=8086,
    INFLUXDB_HOST="localhost",
    INFLUXDB_USER="",
    INFLUXDB_USER_PASSWORD="",
    # named this way to match environment variable used by the influxdb docker image
    INFLUXDB_DB="",
    CREDITS_HISTORY_DB="credits_history",
    MAIL_FROM="CreditsService@denbi.de",
    MAIL_SMTP_SERVER="localhost",
    MAIL_SMTP_PORT=25,
    MAIL_SMTP_USER="",
    MAIL_SMTP_PASSWORD="",
    MAIL_NOT_STARTTLS=False,
    CLOUD_GOVERNANCE_MAIL="",
    NOTIFICATION_TO_OVERWRITE="",
)


def parse_config_from_environment() -> Config:
    # for environment variables that need to be processed
    PROCESSED_ENV_CONFIG: Dict[str, Any] = {}

    try:
        PROCESSED_ENV_CONFIG.update(
            {
                "OS_CREDITS_PROJECT_WHITELIST": set(
                    environ["OS_CREDITS_PROJECT_WHITELIST"].split(";")
                )
            }
        )
    except KeyError:
        # Environment variable not set, that's ok
        pass
    for bool_value in ["MAIL_NOT_STARTTLS"]:
        if bool_value in environ:
            PROCESSED_ENV_CONFIG.update({bool_value: True})

    for int_value_key in [
        "OS_CREDITS_PRECISION",
        "OS_CREDITS_WORKERS",
        "INFLUXDB_PORT",
        "OS_CREDITS_PERUN_VO_ID",
        "MAIL_SMTP_PORT",
    ]:
        try:
            int_value = int(environ[int_value_key])
            if int_value < 0:
                internal_logger.warning(
                    "Integer value (%s) must not be negative, falling back to default value",
                    int_value_key,
                )
                del environ[int_value_key]
                continue
            PROCESSED_ENV_CONFIG.update({int_value_key: int_value})
            internal_logger.debug(f"Added {int_value_key} to procssed env")
        except KeyError:
            # Environment variable not set, that's ok
            pass
        except ValueError:
            internal_logger.warning(
                "Could not convert value of $%s('%s') to int",
                int_value_key,
                environ[int_value_key],
            )
            # since we cannot use a subset of the actual environment, see below, we have
            # to remove invalid keys from environment to make sure that if such a key is
            # looked up inside the config the chainmap does not return the unprocessed
            # value from the environment but rather the default one
            del environ[int_value_key]

    if "OS_CREDITS_PRECISION" in PROCESSED_ENV_CONFIG:
        PROCESSED_ENV_CONFIG["OS_CREDITS_PRECISION"] = (
            Decimal(10) ** -PROCESSED_ENV_CONFIG["OS_CREDITS_PRECISION"]
        )

    # this would be the right way but makes pytest hang forever -.-'
    # use the workaround explained above and add the raw process environment to the
    # chainmap although this is not really nice :(
    # At least mypy should show an error whenever a config value not defined in
    # :class:`Config` is accessed

    # for key in Config.__annotations__:
    #    # every value which needs processing should already be present in
    #    # PROCESSED_ENV_CONFIG if set in the environment
    #    if key in PROCESSED_ENV_CONFIG:
    #        continue
    #    if key in environ:
    #        PROCESSED_ENV_CONFIG.update({key: environ[key]})
    return cast(Config, PROCESSED_ENV_CONFIG)


class _EmptyConfig(UserDict):
    """
    Used as last element inside the config chainmap. If its :func:`__getitem__` method
    is called the requested value is not available and we have to exit.
    """

    def __getitem__(self, key):
        internal_logger.exception(
            "Config value %s was requested but not known. Appending stacktrace", key
        )
        raise MissingConfigError(f"Missing value for key {key}")


config = cast(
    Config,
    ChainMap(parse_config_from_environment(), environ, default_config, _EmptyConfig()),
)


DEFAULT_LOG_LEVEL = {
    "os_credits.tasks": "DEBUG",
    "os_credits.internal": "DEBUG",
    "os_credits.requests": "INFO",
    "os_credits.influxdb": "DEBUG",
}

DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "task_handler": {
            "format": "[%(task_id)s] %(levelname)-8s %(asctime)s: %(message)s"
        },
        "simple_handler": {
            "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s"
        },
    },
    "filters": {"task_id_filter": {"()": "os_credits.log._TaskIdFilter"}},
    "handlers": {
        "with_task_id": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
            "formatter": "task_handler",
        },
        "simple": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
            "formatter": "simple_handler",
        },
    },
    "loggers": {
        "os_credits.tasks": {
            "level": DEFAULT_LOG_LEVEL["os_credits.tasks"],
            "handlers": ["with_task_id"],
            "filters": ["task_id_filter"],
        },
        "os_credits.internal": {
            "level": DEFAULT_LOG_LEVEL["os_credits.internal"],
            "handlers": ["with_task_id"],
            "filters": ["task_id_filter"],
        },
        "os_credits.requests": {
            "level": DEFAULT_LOG_LEVEL["os_credits.requests"],
            "handlers": ["with_task_id"],
            "filters": ["task_id_filter"],
        },
        "os_credits.influxdb": {
            "level": DEFAULT_LOG_LEVEL["os_credits.influxdb"],
            "handlers": ["with_task_id"],
            "filters": ["task_id_filter"],
        },
        "aioinflux": {
            "level": "DEBUG",
            "handlers": ["with_task_id"],
            "filters": ["task_id_filter"],
        },
    },
}
