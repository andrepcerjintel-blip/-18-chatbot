from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MediaStatus(str, Enum):
    SUCCESS = "SUCCESS"
    MEDIA_PROVIDER_NOT_CONFIGURED = "MEDIA_PROVIDER_NOT_CONFIGURED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class ImageRequest(BaseModel):
    """Requisicao estruturada de imagem. Nunca contem texto livre executavel;
    prompt_hint e descritivo, montado a partir de Character/CharacterState."""

    character_id: str
    conversation_id: str
    prompt_hint: str
    seed: Optional[int] = None
    metadata: dict = Field(default_factory=dict)


class ImageResult(BaseModel):
    status: MediaStatus
    message: str
    image_id: Optional[str] = None
    file_path: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ProviderHealth(BaseModel):
    available: bool
    provider: str
    detail: str = ""


class MediaAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    character_id: str
    conversation_id: str
    media_type: str
    seed: Optional[str] = None
    model: Optional[str] = None
    workflow: Optional[str] = None
    safety_status: str
    status: str
    created_at: datetime
