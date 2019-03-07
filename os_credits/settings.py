from __future__ import annotations

from collections import ChainMap, UserDict
from pathlib import Path
from typing import Any, Optional, TextIO

import toml

from os_credits.exceptions import MissingConfigError
from os_credits.log import internal_logger

REPO_DIR = Path(__file__).parent.parent
# Files are read in this order and the first found will be used
default_config_paths = [
    # config inside repo
    REPO_DIR / "config" / "credits.toml",
    Path("/etc/credits.toml"),
]
default_config_path: Optional[Path] = None
for path in default_config_paths:
    if path.is_file():
        default_config_path = path

DEFAULT_CONFIG = {"number_of_workers": 10, "credits_precision": 2}

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
            "level": "INFO",
            "handlers": ["with_task_id"],
            "filters": ["task_id_filter"],
        },
        "os_credits.internal": {
            "level": "INFO",
            "handlers": ["with_task_id"],
            "filters": ["task_id_filter"],
        },
        "os_credits.requests": {
            "level": "INFO",
            "handlers": ["with_task_id"],
            "filters": ["task_id_filter"],
        },
    },
}


class _Config(UserDict):
    def __init__(self, config: Optional[str] = None):
        super().__init__(toml.loads(config) if config else None)

    def __getitem__(self, key: str) -> Any:
        if not self.data:
            internal_logger.warning(
                "No config file loaded but attribute `%s` was accessed. Trying to load "
                "default config from default path (%s).",
                key,
                default_config_path,
            )
            if not default_config_path:
                raise RuntimeError("Could not load any default config.")
            self.data.update(**toml.loads(default_config_path.read_text()))
        return super().__getitem__(key)


class _EmptyConfig(UserDict):
    """
    Used as last element inside the config chainmap. If its getitem is called the
    requested value is set nowhere and we have to exit.
    """

    def __getitem__(self, key: str) -> Any:
        internal_logger.exception(
            "Config value %s was requested but not known. Appending stacktrace", key
        )
        raise MissingConfigError(f"Missing value for key {key}")


custom_config = _Config()

config = ChainMap(custom_config, DEFAULT_CONFIG, _EmptyConfig())


def load_config(config_io: TextIO) -> _Config:
    """
    Loads the given config. Raises an AssertionError in case a critical value is not
    given.
    :return: Config instance loaded
    """
    global custom_config
    config_str = config_io.read()
    try:
        custom_config.data = toml.loads(config_str)  # type: ignore
    except toml.decoder.TomlDecodeError:  # type: ignore
        internal_logger.exception(
            "Could not parse provided settings file (%s). Aborting, see attached stacktrace",
            config_io.name,
        )
    return custom_config
