from __future__ import annotations


from pathlib import Path
from typing import Optional, Any, TextIO
from logging import getLogger

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


class _Config:
    def __init__(self, config: Optional[str] = None):
        self.data = None
        if config:
            self.data = loads(config)
            assert self.vo_id
            assert self.service_user
            assert self.service_user["login"]
            assert self.service_user["password"]

    def __getattr__(self, name: str) -> Any:
        if not self.data:
            _logger.info(
                "No config file loaded but attribute %s was accessed. Trying to load "
                "default config from default paths (%s).",
                name,
                default_config_paths,
            )
            if not default_config_path:
                raise RuntimeError("Could not load any default config.")
            self.data = loads(default_config_path.read_text())
        if name in self.data:
            return self.data[name]
        return getattr(self, name)


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
