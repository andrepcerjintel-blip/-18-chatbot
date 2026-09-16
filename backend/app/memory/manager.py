"""Memoria de conversa em tres niveis:

A. Short-Term Memory: ultimas N mensagens (lidas diretamente de Message).
B. Conversation Summary: resumo progressivo, persistido em
   CharacterState.conversation_summary.
C. Character State: estado persistente (localizacao, roupa, humor etc.),
   ja modelado em CharacterState.

Este modulo cuida de (A) e (B); (C) e manipulado diretamente pelo
Conversation Engine via CharacterState.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.character_state import CharacterState
from app.models.message import Message

SHORT_TERM_WINDOW = 10
SUMMARY_TRIGGER_EVERY = 12
SUMMARY_MAX_CHARS = 1200


class MemoryManager:
    def __init__(self, db: Session):
        self.db = db

    def short_term_messages(self, conversation_id: str) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(SHORT_TERM_WINDOW)
            .all()[::-1]
        )

    def maybe_update_summary(self, state: CharacterState, conversation_id: str) -> None:
        """Resumo simples e deterministico (concatenacao truncada) das
        ultimas mensagens de usuario. Mantido leve/local para nao depender
        obrigatoriamente do LLM configurado."""
        total = self.db.query(Message).filter(Message.conversation_id == conversation_id).count()
        if total == 0 or total % SUMMARY_TRIGGER_EVERY != 0:
            return

        recent_user_msgs = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(SUMMARY_TRIGGER_EVERY)
            .all()[::-1]
        )
        highlights = " | ".join(m.content.strip()[:80] for m in recent_user_msgs)
        combined = f"{state.conversation_summary} {highlights}".strip()
        state.conversation_summary = combined[-SUMMARY_MAX_CHARS:]
