"""Interface abstrata de geracao de imagem.

O restante da aplicacao (Conversation Engine, Safety Engine, Character
Manager, Chat UI) depende apenas desta interface, nunca de detalhes do
ComfyUI ou de qualquer outro engine especifico. Trocar o engine de geracao
(ComfyUI -> Diffusers -> outro) nao deve exigir mudancas fora de
app.media.*.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.media import ImageRequest, ImageResult, ProviderHealth


class ImageProvider(ABC):
    @abstractmethod
    def generate_image(self, request: ImageRequest) -> ImageResult:
        """Deve SEMPRE retornar um ImageResult estruturado, mesmo em caso de
        erro ou indisponibilidade. Nunca deve lancar excecao nao tratada
        para o chamador (Conversation Engine)."""

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Verifica disponibilidade do provider sem lancar excecao."""
