from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.conversation.engine import ConversationEngine
from app.intent.classifier import IntentClassifier
from app.media.provider_factory import get_image_provider
from app.models.conversation import Conversation
from app.models.media import MediaAsset
from app.schemas.intent import IntentType
from app.schemas.media import MediaAssetRead
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


@router.get("/{media_id}", response_model=MediaAssetRead)
def get_media(media_id: str, db: Session = Depends(get_db)):
    asset = db.get(MediaAsset, media_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="media not found")
    return asset


@router.get("/{media_id}/file")
def get_media_file(media_id: str, db: Session = Depends(get_db)):
    """Serve os bytes da imagem gerada. O caminho no disco nunca e exposto
    diretamente ao cliente (ver MediaAssetRead) -- apenas este endpoint
    resolve id -> arquivo, e apenas se o arquivo realmente existir."""
    asset = db.get(MediaAsset, media_id)
    if asset is None or not asset.file_path:
        raise HTTPException(status_code=404, detail="media not found")

    file_path = Path(asset.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="media file missing on disk")

    return FileResponse(file_path, media_type="image/png")
