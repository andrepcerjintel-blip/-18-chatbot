from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.conversation.engine import ConversationEngine
from app.media.provider_factory import get_image_provider
from app.models.conversation import Conversation
from app.schemas.intent import IntentType
from app.services.intent_classifier import IntentClassifier
from app.services.llm.factory import get_llm_provider

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/image")
def request_image(conversation_id: str, db: Session = Depends(get_db)):
    """Endpoint direto para solicitar imagem fora do fluxo de chat (usado
    por controles opcionais do frontend). Passa pelo mesmo Conversation
    Engine, garantindo que Safety Engine e regras sejam sempre aplicados."""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    engine = ConversationEngine(
        db,
        intent_classifier=IntentClassifier(),
        image_provider=get_image_provider(),
        llm_provider=get_llm_provider(),
    )
    response = engine.handle_message(conversation, "manda uma foto")
    return response


@router.get("/{media_id}")
def get_media(media_id: str, db: Session = Depends(get_db)):
    from app.models.media import MediaAsset

    asset = db.get(MediaAsset, media_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="media not found")
    return asset
