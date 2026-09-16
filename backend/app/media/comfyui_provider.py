"""ComfyUIProvider -- modo stub/configuravel (Fase 1).

Nesta fase, NAO escolhemos checkpoint, resolucao, batch size, precisao,
quantizacao, offloading ou attention backend -- essas decisoes dependem do
hardware real (GPU/VRAM/CUDA), que ainda e UNKNOWN. Este provider apenas:

  1. sabe conversar com um ComfyUI local via HTTP (health check);
  2. reporta de forma honesta que a geracao efetiva ainda nao esta
     disponivel, via MEDIA_PROVIDER_NOT_CONFIGURED, em vez de fingir sucesso
     ou lancar excecao.

Quando o hardware for conhecido (Secao 22 do briefing), a geracao real
(workflow loader, fila de jobs, parametros de VRAM) sera implementada aqui
sem alterar a interface ImageProvider nem o restante da aplicacao.
"""
from __future__ import annotations

import urllib.error
import urllib.request

from app.config import get_settings
from app.logging_config import logger
from app.media.provider_base import ImageProvider
from app.schemas.media import ImageRequest, ImageResult, MediaStatus, ProviderHealth


class ComfyUIProvider(ImageProvider):
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate_image(self, request: ImageRequest) -> ImageResult:
        try:
            if not self.settings.image_model_path:
                return ImageResult(
                    status=MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED,
                    message=(
                        "ComfyUI provider is set, but no visual checkpoint (IMAGE_MODEL_PATH) "
                        "has been configured yet. This depends on the real GPU/VRAM being known."
                    ),
                    metadata={},
                )
            health = self.health_check()
            if not health.available:
                return ImageResult(
                    status=MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED,
                    message=f"ComfyUI is not reachable at {self.settings.comfyui_url}: {health.detail}",
                    metadata={},
                )
            # Geracao real (workflow loader, fila de jobs, chamada a /prompt)
            # e implementada na Fase 2, apos hardware e checkpoint definidos.
            return ImageResult(
                status=MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED,
                message="ComfyUI is reachable, but the generation pipeline is not implemented yet (Phase 2).",
                metadata={"comfyui_url": self.settings.comfyui_url},
            )
        except Exception:
            logger.exception("comfyui_provider_generate_image_exception")
            return ImageResult(
                status=MediaStatus.ERROR,
                message="Unexpected error while attempting image generation.",
                metadata={},
            )

    def health_check(self) -> ProviderHealth:
        url = f"{self.settings.comfyui_url.rstrip('/')}/system_stats"
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310 (local trusted URL)
                if resp.status == 200:
                    return ProviderHealth(available=True, provider="comfyui", detail="reachable")
                return ProviderHealth(
                    available=False, provider="comfyui", detail=f"unexpected status {resp.status}"
                )
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            return ProviderHealth(available=False, provider="comfyui", detail=str(exc))
