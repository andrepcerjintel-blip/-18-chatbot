from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    CHAT = "CHAT"
    IMAGE_REQUEST = "IMAGE_REQUEST"
    VIDEO_REQUEST = "VIDEO_REQUEST"
    CHANGE_OUTFIT = "CHANGE_OUTFIT"
    CHANGE_LOCATION = "CHANGE_LOCATION"
    CHANGE_STATE = "CHANGE_STATE"
    UNSAFE_REQUEST = "UNSAFE_REQUEST"


class IntentResult(BaseModel):
    """Saida do Intent Classifier. Sempre validada por este schema antes de
    ser usada; texto livre de LLM nunca vira comando executavel diretamente."""

    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    matched_rule: str = ""
