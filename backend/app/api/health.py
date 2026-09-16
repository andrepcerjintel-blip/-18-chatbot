from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.media.provider_factory import get_image_provider
from app.services.llm.factory import get_llm_provider

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    image_provider = get_image_provider()
    llm_provider = get_llm_provider()
    media_health = image_provider.health_check()
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "llm_provider": type(llm_provider).__name__,
        "media_provider": {
            "name": media_health.provider,
            "available": media_health.available,
            "detail": media_health.detail,
        },
        "hardware": {
            "gpu_model": settings.gpu_model,
            "gpu_vram_gb": settings.gpu_vram_gb,
            "cuda_version": settings.cuda_version,
        },
    }
