from pathlib import Path
from typing import Optional, Any
from logging import getLogger

from toml import load

BASE_DIR = Path(__file__).parent.parent
default_config_path = BASE_DIR / "config" / "credits.toml"
_logger = getLogger(__name__)


class _Config:
    def __init__(self, config_path: Optional[Path] = None):
        self.data = None
        if config_path:
            self.data = load(config_path)
            try:
                assert self["vo_id"]
                assert self["service_user"]
                assert self["service_user"]["login"]
                assert self["service_user"]["password"]
            except AssertionError as e:
                _logger.critical("Missing critical setting for %s. Aborting", e)

    def __getattr__(self, name: str) -> Any:
        if not self.data:
            self.data = load(default_config_path)
        if name in self.data:
            return self.data[name]
        return getattr(self, name)


config = _Config()
