from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    character_id: str


class CharacterStateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location: str
    time_of_day: str
    outfit: str
    hair_state: str
    mood: str
    last_pose: str
    last_generated_media: Optional[str] = None
    conversation_summary: str


class MessageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    intent: Optional[str] = None
    safety_status: Optional[str] = None
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    character_id: str
    created_at: datetime
    updated_at: datetime
    state: CharacterStateSchema
    messages: list[MessageSchema] = []
