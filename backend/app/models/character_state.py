from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CharacterState(Base):
    """Estado persistente de uma personagem dentro de uma conversa especifica.

    Mantido para dar continuidade (roupa, cenario, humor, pose) entre
    mensagens de texto e futuras geracoes de imagem/video.
    """

    __tablename__ = "character_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    location: Mapped[str] = mapped_column(String(200), nullable=False, default="quarto")
    time_of_day: Mapped[str] = mapped_column(String(50), nullable=False, default="noite")
    outfit: Mapped[str] = mapped_column(String(300), nullable=False, default="roupas casuais")
    hair_state: Mapped[str] = mapped_column(String(200), nullable=False, default="solto")
    mood: Mapped[str] = mapped_column(String(100), nullable=False, default="tranquila")
    last_pose: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    last_generated_media: Mapped[str] = mapped_column(String(500), nullable=True, default=None)
    conversation_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="state")

    # Campos que podem ser alterados por intents de conversa (CHANGE_*).
    MUTABLE_FIELDS: frozenset[str] = frozenset(
        {"location", "time_of_day", "outfit", "hair_state", "mood", "last_pose"}
    )
