from __future__ import annotations

from app.media.provider_base import ImageProvider
from app.schemas.media import ImageRequest, ImageResult, MediaStatus, ProviderHealth


class NullImageProvider(ImageProvider):
    """Provider usado enquanto nenhum gerador visual esta configurado.

    Garante que solicitacoes de imagem/video nao quebrem a conversa: sempre
    retorna um status estruturado MEDIA_PROVIDER_NOT_CONFIGURED.
    """

    def generate_image(self, request: ImageRequest) -> ImageResult:
        return ImageResult(
            status=MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED,
            message="Local image generation has not been configured yet.",
            image_id=None,
            file_path=None,
            metadata={},
        )

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            available=False,
            provider="null",
            detail="No media provider configured (MEDIA_PROVIDER=null).",
        )
