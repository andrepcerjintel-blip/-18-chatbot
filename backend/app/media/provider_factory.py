from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.logging_config import logger
from app.media.comfyui_provider import ComfyUIProvider
from app.media.null_provider import NullImageProvider
from app.media.provider_base import ImageProvider


@lru_cache
def get_image_provider() -> ImageProvider:
    settings = get_settings()
    provider_name = settings.media_provider.lower().strip()
    if provider_name == "comfyui":
        logger.info("provider_status media_provider=comfyui")
        return ComfyUIProvider()
    if provider_name not in ("", "null"):
        logger.warning("provider_status unknown_media_provider=%s falling_back=null", provider_name)
    logger.info("provider_status media_provider=null")
    return NullImageProvider()
