"""Configuración de logs seguros con fechas en UTC."""

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path


class UtcFormatter(logging.Formatter):
    """Formateador que nunca depende de la zona horaria local del proceso."""

    converter = staticmethod(time.gmtime)


def configure_logging(
    log_level: str, log_directory: Path = Path("logs")
) -> logging.Logger:
    """Configura consola y archivo rotativo para la ejecución del bot."""
    log_directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("codex_bot")
    logger.setLevel(log_level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = UtcFormatter(
        "%(asctime)sZ %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        log_directory / "chat.log",
        encoding="utf-8",
        maxBytes=1_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
