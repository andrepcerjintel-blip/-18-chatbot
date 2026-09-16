from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.conversation import CharacterStateSchema
from app.schemas.intent import IntentType
from app.schemas.media import ImageResult
from app.schemas.safety import SafetyDecision, SafetyReason


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    conversation_id: str
    intent: IntentType
    safety_decision: SafetyDecision
    safety_reasons: list[SafetyReason] = Field(default_factory=list)
    reply: Optional[str] = None
    media: Optional[ImageResult] = None
    state: Optional[CharacterStateSchema] = None
