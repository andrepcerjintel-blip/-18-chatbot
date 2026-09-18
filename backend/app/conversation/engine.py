"""Conversation Engine.

Orquestra o fluxo:
  USER_INPUT -> Intent Classifier -> Safety Engine -> Character State
  -> (Prompt Builder / LLM) ou (ImageProvider) -> Post-generation Safety
  -> Chat UI

Principios de seguranca aplicados aqui:
  - USER_INPUT e sempre tratado como nao confiavel; nunca e usado para
    alterar campos protegidos de Character (age, synthetic, id, created_at).
  - O Safety Engine roda SEMPRE, independente do intent, antes de qualquer
    resposta de texto ou geracao de midia (fail-closed).
  - Atualizacoes de CharacterState (CHANGE_OUTFIT/LOCATION/STATE) tocam
    apenas CharacterState.MUTABLE_FIELDS, nunca a entidade Character.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.character.manager import CharacterManager
from app.intent.classifier import IntentClassifier
from app.logging_config import logger
from app.media.provider_base import ImageProvider
from app.memory.manager import MemoryManager
from app.models.character_state import CharacterState
from app.models.conversation import Conversation
from app.models.media import MediaAsset
from app.models.message import Message
from app.safety.engine import SafetyEngine
from app.schemas.chat import ChatResponse
from app.schemas.conversation import CharacterStateSchema
from app.schemas.intent import IntentType
from app.schemas.media import ImageRequest, MediaStatus
from app.schemas.safety import SafetyDecision
from app.services.llm.base import LLMCharacterContext, LLMProvider

_BLOCKED_REPLY = (
    "Não posso continuar com esse pedido. Ele viola as regras de segurança "
    "deste aplicativo e foi bloqueado."
)


class ConversationEngine:
    def __init__(
        self,
        db: Session,
        *,
        intent_classifier: IntentClassifier | None = None,
        safety_engine: SafetyEngine | None = None,
        image_provider: ImageProvider,
        llm_provider: LLMProvider,
    ):
        self.db = db
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.safety_engine = safety_engine or SafetyEngine()
        self.image_provider = image_provider
        self.llm_provider = llm_provider
        self.character_manager = CharacterManager(db)
        self.memory = MemoryManager(db)

    def handle_message(self, conversation: Conversation, user_text: str) -> ChatResponse:
        state = conversation.state
        character = conversation.character

        intent_result = self.intent_classifier.classify(user_text)
        safety_result = self.safety_engine.pre_generation_check(text=user_text)

        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=user_text,
            intent=intent_result.intent.value,
            safety_status=safety_result.decision.value,
        )
        self.db.add(user_message)

        if safety_result.decision == SafetyDecision.BLOCK:
            logger.warning(
                "unsafe_request_blocked conversation_id=%s reasons=%s",
                conversation.id,
                [r.value for r in safety_result.reasons],
            )
            self.db.add(
                Message(conversation_id=conversation.id, role="assistant", content=_BLOCKED_REPLY, intent=IntentType.UNSAFE_REQUEST.value, safety_status=SafetyDecision.BLOCK.value)
            )
            self.db.commit()
            return ChatResponse(
                conversation_id=conversation.id,
                intent=IntentType.UNSAFE_REQUEST,
                safety_decision=safety_result.decision,
                safety_reasons=safety_result.reasons,
                reply=_BLOCKED_REPLY,
                state=CharacterStateSchema.model_validate(state),
            )

        if intent_result.intent in (IntentType.IMAGE_REQUEST, IntentType.VIDEO_REQUEST):
            media_result = self._handle_media_request(conversation, state, intent_result.intent, user_text)
            self.db.add(
                Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=media_result.message,
                    intent=intent_result.intent.value,
                    safety_status=safety_result.decision.value,
                    media_id=media_result.image_id if media_result.status == MediaStatus.SUCCESS else None,
                )
            )
            self.db.commit()
            return ChatResponse(
                conversation_id=conversation.id,
                intent=intent_result.intent,
                safety_decision=safety_result.decision,
                safety_reasons=safety_result.reasons,
                reply=media_result.message,
                media=media_result,
                state=CharacterStateSchema.model_validate(state),
            )

        if intent_result.intent in (IntentType.CHANGE_OUTFIT, IntentType.CHANGE_LOCATION, IntentType.CHANGE_STATE):
            self._apply_state_change(state, intent_result.intent, user_text)
            reply = self._generate_reply(character, state, conversation.id, user_text)
            self.db.add(
                Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=reply,
                    intent=intent_result.intent.value,
                    safety_status=safety_result.decision.value,
                )
            )
            self.memory.maybe_update_summary(state, conversation.id)
            self.db.commit()
            return ChatResponse(
                conversation_id=conversation.id,
                intent=intent_result.intent,
                safety_decision=safety_result.decision,
                safety_reasons=safety_result.reasons,
                reply=reply,
                state=CharacterStateSchema.model_validate(state),
            )

        # CHAT (default)
        reply = self._generate_reply(character, state, conversation.id, user_text)
        post_check = self.safety_engine.post_generation_check(output_text=reply)
        if post_check.decision == SafetyDecision.BLOCK:
            reply = _BLOCKED_REPLY

        self.db.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=reply,
                intent=IntentType.CHAT.value,
                safety_status=post_check.decision.value,
            )
        )
        self.memory.maybe_update_summary(state, conversation.id)
        self.db.commit()
        return ChatResponse(
            conversation_id=conversation.id,
            intent=IntentType.CHAT,
            safety_decision=post_check.decision,
            safety_reasons=post_check.reasons,
            reply=reply,
            state=CharacterStateSchema.model_validate(state),
        )

    def _apply_state_change(self, state: CharacterState, intent: IntentType, user_text: str) -> None:
        """Atualiza apenas CharacterState.MUTABLE_FIELDS. Nunca toca em
        Character (id/age/synthetic/created_at permanecem intocaveis)."""
        cleaned = user_text.strip()[:300]
        if intent == IntentType.CHANGE_OUTFIT:
            state.outfit = cleaned
        elif intent == IntentType.CHANGE_LOCATION:
            state.location = cleaned
        elif intent == IntentType.CHANGE_STATE:
            state.mood = cleaned

    def _generate_reply(self, character, state: CharacterState, conversation_id: str, user_text: str) -> str:
        personality = character.personality
        context = LLMCharacterContext(
            name=character.name,
            age=character.age,
            gender=character.gender,
            appearance=character.appearance,
            personality={
                "shyness": personality.shyness,
                "extroversion": personality.extroversion,
                "initiative": personality.initiative,
                "romanticism": personality.romanticism,
                "sexual_openness": personality.sexual_openness,
                "playfulness": personality.playfulness,
                "assertiveness": personality.assertiveness,
                "affection": personality.affection,
            },
            state={
                "location": state.location,
                "time_of_day": state.time_of_day,
                "outfit": state.outfit,
                "hair_state": state.hair_state,
                "mood": state.mood,
            },
            conversation_summary=state.conversation_summary,
            short_term_messages=[(m.role, m.content) for m in self.memory.short_term_messages(conversation_id)],
        )
        try:
            return self.llm_provider.generate_reply(context=context, user_text=user_text)
        except Exception:
            logger.exception("llm_provider_generate_reply_exception")
            return "Desculpa, tive um problema para responder agora. Pode tentar novamente?"

    def _handle_media_request(
        self, conversation: Conversation, state: CharacterState, intent: IntentType, user_text: str
    ):
        from app.schemas.media import ImageResult

        if intent == IntentType.VIDEO_REQUEST:
            logger.info("media_job type=video status=not_configured conversation_id=%s", conversation.id)
            return ImageResult(
                status=MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED,
                message="Local video generation has not been configured yet.",
            )

        character = conversation.character
        prompt_hint = self._build_image_prompt(character, state, user_text)
        request = ImageRequest(
            character_id=conversation.character_id,
            conversation_id=conversation.id,
            prompt_hint=prompt_hint,
        )
        try:
            result = self.image_provider.generate_image(request)
        except Exception:
            logger.exception("image_provider_generate_image_exception")
            return ImageResult(status=MediaStatus.ERROR, message="Unexpected error generating image.")

        logger.info("media_job type=image status=%s conversation_id=%s", result.status.value, conversation.id)

        if result.status == MediaStatus.SUCCESS:
            post_check = self.safety_engine.post_generation_check(media_meta=result.metadata)
            if post_check.decision == SafetyDecision.BLOCK:
                logger.warning("media_post_check_blocked conversation_id=%s", conversation.id)
                return ImageResult(status=MediaStatus.BLOCKED, message="Generated media was blocked by safety checks.")
            state.last_generated_media = result.file_path
            self.db.add(
                MediaAsset(
                    id=result.image_id,
                    character_id=conversation.character_id,
                    conversation_id=conversation.id,
                    file_path=result.file_path,
                    media_type="image",
                    seed=str(result.metadata.get("seed", "")) or None,
                    model=result.metadata.get("model"),
                    workflow=result.metadata.get("workflow"),
                    safety_status=post_check.decision.value,
                    status=result.status.value,
                )
            )

        return result

    _SUBJECT_TAG_BY_GENDER = {"female": "1woman, solo", "male": "1man, solo"}

    @classmethod
    def _build_image_prompt(cls, character, state: CharacterState, user_text: str) -> str:
        """Monta um prompt descritivo a partir da ficha do personagem, do
        estado da conversa, e do pedido especifico desta mensagem.

        user_text ja passou pelo SafetyEngine.pre_generation_check antes
        deste ponto (handle_message roda a checagem para toda mensagem,
        independente do intent) -- sem isso, o texto do usuario nunca era
        incluido no prompt de imagem, e o modelo gerava cenarios genericos
        (ex.: um quarto vazio) em vez do que a pessoa realmente pediu."""
        subject_tag = cls._SUBJECT_TAG_BY_GENDER.get(character.gender.lower(), "1person, solo")
        parts = [
            subject_tag,
            character.appearance,
            f"{character.hair} hair" if character.hair else "",
            f"{character.eyes} eyes" if character.eyes else "",
            character.body_description,
            state.outfit,
            f"in {state.location}" if state.location else "",
            state.time_of_day,
            f"{state.mood} mood" if state.mood else "",
            state.last_pose,
            "portrait, looking at viewer",
            user_text.strip()[:200],
        ]
        return ", ".join(p.strip() for p in parts if p and p.strip())
