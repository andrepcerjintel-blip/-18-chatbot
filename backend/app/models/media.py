from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MediaAsset(Base):
    """Metadata de midia gerada. Fase 1: estrutura preparada, sem geracao real."""

    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    character_id: Mapped[str] = mapped_column(String(36), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=True)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, default="image")
    seed: Mapped[str] = mapped_column(String(50), nullable=True)
    model: Mapped[str] = mapped_column(String(200), nullable=True)
    workflow: Mapped[str] = mapped_column(String(200), nullable=True)
    safety_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ALLOW")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="MEDIA_PROVIDER_NOT_CONFIGURED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
