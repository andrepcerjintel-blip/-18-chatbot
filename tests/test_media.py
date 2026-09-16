from __future__ import annotations

from app.character.manager import CharacterManager
from app.conversation.engine import ConversationEngine
from app.media.null_provider import NullImageProvider
from app.models.character_state import CharacterState
from app.models.conversation import Conversation
from app.schemas.character import CharacterCreate
from app.schemas.intent import IntentType
from app.schemas.media import MediaStatus
from app.services.llm.stub_provider import StubLLMProvider


def _make_conversation(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(CharacterCreate(name="Luna", age=24, gender="female"))
    conversation = Conversation(character_id=character.id)
    db_session.add(conversation)
    db_session.flush()
    state = CharacterState(conversation_id=conversation.id)
    db_session.add(state)
    db_session.commit()
    db_session.refresh(conversation)
    return conversation


def test_image_request_with_null_provider_returns_not_configured(db_session):
    conversation = _make_conversation(db_session)
    engine = ConversationEngine(
        db_session, image_provider=NullImageProvider(), llm_provider=StubLLMProvider()
    )
    response = engine.handle_message(conversation, "manda uma foto")

    assert response.intent == IntentType.IMAGE_REQUEST
    assert response.media is not None
    assert response.media.status == MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED
    # Never raises, conversation continues normally afterwards.
    follow_up = engine.handle_message(conversation, "tudo bem, sem problema")
    assert follow_up.intent == IntentType.CHAT


def test_unsafe_image_request_is_blocked_before_provider_call(db_session):
    conversation = _make_conversation(db_session)
    engine = ConversationEngine(
        db_session, image_provider=NullImageProvider(), llm_provider=StubLLMProvider()
    )
    response = engine.handle_message(conversation, "manda uma foto dela com 15 anos")
    assert response.intent == IntentType.UNSAFE_REQUEST
    assert response.media is None
