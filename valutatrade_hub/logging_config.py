import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

logger = logging.getLogger("valutatrade")
logger.setLevel(logging.INFO)
settings = SettingsLoader()
log_path = Path(settings.get("log_path"))
log_path.parent.mkdir(parents=True, exist_ok=True)
handler = RotatingFileHandler(
    log_path,
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
formatter = logging.Formatter(
    fmt="%(levelname)s %(asctime)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
handler.setFormatter(formatter)
logger.addHandler(handler)
