from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.conversation.engine import ConversationEngine
from app.media.provider_factory import get_image_provider
from app.models.conversation import Conversation
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.intent_classifier import IntentClassifier
from app.services.llm.factory import get_llm_provider

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, payload.conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    engine = ConversationEngine(
        db,
        intent_classifier=IntentClassifier(),
        image_provider=get_image_provider(),
        llm_provider=get_llm_provider(),
    )
    return engine.handle_message(conversation, payload.message)
