from __future__ import annotations

from collections import UserDict
from logging import getLogger
from pathlib import Path
from typing import Any, Optional, TextIO

from toml import loads

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

_logger = getLogger(__name__)


class _Config(UserDict):
    def __init__(self, config: Optional[str] = None):
        super().__init__()
        if config:
            self.data.update(**loads(config))
            assert self["vo_id"]
            assert self["service_user"]
            assert self["service_user"]["login"]
            assert self["service_user"]["password"]

    def __getitem__(self, key: str) -> Any:
        if not self.data:
            _logger.info(
                "No config file loaded but attribute %s was accessed. Trying to load "
                "default config from default paths (%s).",
                key,
                default_config_paths,
            )
            if not default_config_path:
                raise RuntimeError("Could not load any default config.")
            self.data.update(**loads(default_config_path.read_text()))
        return super().__getitem__(key)


def load_config(config_io: TextIO) -> _Config:
    """
    Loads the given config. Raises an AssertionError in case a critical value is not
    given.
    :return: Config instance loaded
    """
    global config
    config_str = config_io.read()
    config = _Config(config_str)
    return config


config = _Config()
