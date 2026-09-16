from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

MIN_CHARACTER_AGE = 21


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Character(Base):
    """Personagem sintetico e persistente.

    Invariantes protegidas contra alteracao por texto livre de conversa:
    - age (sempre >= MIN_CHARACTER_AGE)
    - synthetic (sempre True)
    - id / created_at (imutaveis)
    Essas invariantes sao reforcadas em app.character.manager, nunca no
    caminho de conversa/chat.
    """

    __tablename__ = "characters"
    __table_args__ = (
        CheckConstraint(f"age >= {MIN_CHARACTER_AGE}", name="ck_character_min_age"),
        CheckConstraint("synthetic = 1", name="ck_character_synthetic_true"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    gender: Mapped[str] = mapped_column(String(50), nullable=False)

    appearance: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hair: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    eyes: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    skin: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    height: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    body_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    distinctive_features: Mapped[str] = mapped_column(Text, nullable=False, default="")

    visual_identity_reference: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    personality: Mapped["PersonalityProfile"] = relationship(
        back_populates="character", uselist=False, cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )

    # Campos protegidos contra alteracao vinda de conversa/texto livre do usuario.
    PROTECTED_FIELDS: frozenset[str] = frozenset({"id", "age", "synthetic", "created_at"})
