from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.character.manager import CharacterManager
from app.models.character_state import CharacterState
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationRead

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=201)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    character = CharacterManager(db).get(payload.character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    conversation = Conversation(character_id=character.id)
    db.add(conversation)
    db.flush()

    state = CharacterState(conversation_id=conversation.id)
    db.add(state)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation
