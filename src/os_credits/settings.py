from __future__ import annotations

from collections import ChainMap, UserDict
from os import environ
from typing import Any, Dict

from os_credits.exceptions import MissingConfigError
from os_credits.log import internal_logger

DEFAULT_CONFIG = {
    "OS_CREDITS_PERUN_LOGIN": "",
    "OS_CREDITS_PERUN_PASSWORD": "",
    "OS_CREDITS_PERUN_VO_ID": 0,
    "OS_CREDITS_WORKERS": 10,
    "OS_CREDITS_PRECISION": 2,
    "INFLUXDB_PORT": 8086,
    "INFLUXDB_HOST": "localhost",
    "INFLUXDB_USER": "",
    "INFLUXDB_USER_PASSWORD": "",
    # named this way to match environment variable used by the influxdb docker image
    "INFLUXDB_DB": "",
    "CREDITS_HISTORY_DB": "credits_history",
    "MAIL_FROM": "CreditsService@denbi.de",
    "MAIL_SMTP_SERVER": "localhost",
    "MAIL_SMTP_PORT": 25,
    "MAIL_SMTP_USER": "",
    "MAIL_SMTP_PASSWORD": "",
    "MAIL_NOT_STARTTLS": False,
    "CLOUD_GOVERNANCE_MAIL": "",
}

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

for int_value in [
    "OS_CREDITS_PRECISION",
    "OS_CREDITS_WORKERS",
    "INFLUXDB_PORT",
    "OS_CREDITS_PERUN_VO_ID",
    "MAIL_SMTP_PORT",
]:
    try:
        PROCESSED_ENV_CONFIG.update({int_value: int(environ[int_value])})
    except KeyError:
        # Environment variable not set, that's ok
        pass
    except ValueError:
        internal_logger.warning("Could not convert value of $%s to int", int_value)

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


class _EmptyConfig(UserDict):
    """
    Used as last element inside the config chainmap. If its getitem is called the
    requested value is set nowhere and we have to exit.
    """

    def __getitem__(self, key):
        internal_logger.exception(
            "Config value %s was requested but not known. Appending stacktrace", key
        )
        raise MissingConfigError(f"Missing value for key {key}")


config = ChainMap(
    PROCESSED_ENV_CONFIG,
    # TODO: Find out why the code below makes pytest hang
    # {key: environ[key] for key in DEFAULT_CONFIG if key in environ},
    environ,
    DEFAULT_CONFIG,
    _EmptyConfig(),
)
