from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.hardware.profile import get_hardware_profile
from app.media.provider_factory import get_image_provider
from app.services.llm.factory import get_llm_provider

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    image_provider = get_image_provider()
    llm_provider = get_llm_provider()
    media_health = image_provider.health_check()
    hardware = get_hardware_profile()
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "llm_provider": type(llm_provider).__name__,
        "media_provider": {
            "name": media_health.provider,
            "available": media_health.available,
            "detail": media_health.detail,
        },
        "hardware": hardware.model_dump(),
    }


@router.get("/hardware")
def hardware():
    """Expoe o HardwareProfile estruturado e desacoplado de vendor. Somente
    leitura: reflete o que foi registrado em .env (via scripts/audit_env.py
    ou manualmente), nunca detecta ou instala nada em tempo de requisicao."""
    return get_hardware_profile().model_dump()
