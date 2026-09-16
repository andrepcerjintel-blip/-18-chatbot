"""Logging tecnico da aplicacao.

Nunca registrar: conteudo intimo completo das mensagens, tokens de API,
chaves ou credenciais. Eventos de negocio (safety_decision, media_job,
intent_classification etc.) sao logados com metadados minimos.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.config import get_settings


def configure_logging() -> logging.Logger:
    settings = get_settings()
    logs_dir = Path(settings.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("companion_app")
    if logger.handlers:
        return logger

    logger.setLevel(settings.log_level.upper())

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


logger = configure_logging()
