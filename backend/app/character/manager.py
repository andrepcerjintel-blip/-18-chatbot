"""Character Manager.

Unico ponto de escrita para a entidade Character/PersonalityProfile.
Garante as invariantes:
  - age >= MIN_CHARACTER_AGE (21)
  - aparencia descrita nunca pode sugerir menoridade/juventude, INDEPENDENTE
    da idade declarada (uma idade adulta nao autoriza, por si so, uma
    aparencia infantil/adolescente -- ver SafetyEngine.check_character_definition)
  - synthetic == True sempre
  - identity_origin == "synthetic_generation" sempre
  - real_person_reference sempre vazio/nulo
  - id / created_at imutaveis
  - gender e obrigatorio (nunca presumido) e restrito a valores suportados
  - campos protegidos nunca aceitam alteracao vinda de texto de conversa

O Conversation Engine NUNCA deve tocar diretamente no ORM de Character;
toda mutacao passa por aqui, e apenas via CharacterUpdate (schema que ja
exclui os campos protegidos em tempo de tipagem).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.logging_config import logger
from app.models.character import DEFAULT_IDENTITY_ORIGIN, MIN_CHARACTER_AGE, Character
from app.models.personality import PersonalityProfile
from app.personality.presets import PERSONALITY_FIELD_NAMES, PERSONALITY_PRESETS
from app.safety.engine import SafetyEngine
from app.schemas.character import CharacterCreate, CharacterUpdate
from app.schemas.safety import SafetyResult

_APPEARANCE_FIELDS = (
    "appearance",
    "hair",
    "eyes",
    "skin",
    "height",
    "body_description",
    "distinctive_features",
)


class ProtectedFieldError(Exception):
    """Levantado quando uma tentativa de alterar um campo protegido ocorre."""


class UnsafeCharacterError(Exception):
    """Levantado quando a ficha do personagem (idade e/ou aparencia
    descrita) e reprovada pelo Safety Engine. Idade adulta declarada NAO
    e suficiente por si so -- ver SafetyEngine.check_character_definition."""

    def __init__(self, result: SafetyResult):
        self.result = result
        super().__init__(f"unsafe character definition: {[r.value for r in result.reasons]}")


def _appearance_text(**fields: str) -> str:
    return " ".join(v for v in fields.values() if v)


class CharacterManager:
    def __init__(self, db: Session):
        self.db = db
        self.safety_engine = SafetyEngine()

    def create(self, payload: CharacterCreate) -> Character:
        if payload.age < MIN_CHARACTER_AGE:
            # Defesa em profundidade: o schema ja bloqueia isso, mas
            # nunca confiamos em uma unica camada de validacao.
            raise ValueError(f"age must be >= {MIN_CHARACTER_AGE}")

        appearance_text = _appearance_text(**{f: getattr(payload, f) for f in _APPEARANCE_FIELDS})
        safety_result = self.safety_engine.check_character_definition(
            age=payload.age, appearance_text=appearance_text
        )
        if safety_result.blocked:
            logger.warning(
                "unsafe_character_creation_blocked name=%s reasons=%s",
                payload.name,
                [r.value for r in safety_result.reasons],
            )
            raise UnsafeCharacterError(safety_result)

        character = Character(
            name=payload.name,
            age=payload.age,
            synthetic=True,
            gender=payload.gender,
            appearance=payload.appearance,
            hair=payload.hair,
            eyes=payload.eyes,
            skin=payload.skin,
            height=payload.height,
            body_description=payload.body_description,
            distinctive_features=payload.distinctive_features,
            visual_identity_reference=payload.visual_identity_reference,
            # Protegidos: sempre controlados pelo servidor, nunca pelo cliente.
            identity_origin=DEFAULT_IDENTITY_ORIGIN,
            real_person_reference=None,
        )
        self.db.add(character)
        self.db.flush()

        params = dict.fromkeys(PERSONALITY_FIELD_NAMES, 50)
        preset_name = "CUSTOM"
        if payload.personality_preset is not None:
            preset_name = payload.personality_preset.value
            preset_values = PERSONALITY_PRESETS.get(preset_name)
            if preset_values:
                params.update(preset_values)
        if payload.personality is not None:
            preset_name = payload.personality.preset.value
            params.update(payload.personality.model_dump(exclude={"preset"}))

        personality = PersonalityProfile(character_id=character.id, preset=preset_name, **params)
        self.db.add(personality)
        self.db.commit()
        self.db.refresh(character)
        logger.info("character_created id=%s name=%s age=%s", character.id, character.name, character.age)
        return character

    def get(self, character_id: str) -> Character | None:
        return self.db.get(Character, character_id)

    def list(self) -> list[Character]:
        return list(self.db.query(Character).order_by(Character.created_at.desc()).all())

    def update(self, character_id: str, payload: CharacterUpdate) -> Character:
        """Aplica apenas campos presentes em CharacterUpdate, que ja exclui
        por construcao id/age/synthetic/created_at. Qualquer tentativa de
        passar um campo protegido (ex.: via dict externo) e explicitamente
        rejeitada aqui tambem, em defesa de profundidade."""
        character = self.get(character_id)
        if character is None:
            raise LookupError(f"character {character_id} not found")

        updates = payload.model_dump(exclude_unset=True)
        for field in updates:
            if field in Character.PROTECTED_FIELDS:
                logger.warning("protected_field_update_blocked character_id=%s field=%s", character_id, field)
                raise ProtectedFieldError(f"field '{field}' is protected and cannot be modified")

        if any(f in updates for f in _APPEARANCE_FIELDS):
            merged = {f: updates.get(f, getattr(character, f)) for f in _APPEARANCE_FIELDS}
            safety_result = self.safety_engine.check_character_definition(
                age=character.age, appearance_text=_appearance_text(**merged)
            )
            if safety_result.blocked:
                logger.warning(
                    "unsafe_character_update_blocked character_id=%s reasons=%s",
                    character_id,
                    [r.value for r in safety_result.reasons],
                )
                raise UnsafeCharacterError(safety_result)

        for field, value in updates.items():
            if value is not None:
                setattr(character, field, value)

        self.db.commit()
        self.db.refresh(character)
        return character

    def reject_conversation_driven_update(self, requested_fields: dict) -> None:
        """Chamado pelo Conversation Engine quando o usuario tenta, via texto
        livre, alterar propriedades protegidas (ex.: idade). Nunca aplica a
        mudanca; apenas loga para auditoria."""
        protected = {k: v for k, v in requested_fields.items() if k in Character.PROTECTED_FIELDS}
        if protected:
            logger.warning("conversation_driven_protected_update_rejected fields=%s", list(protected.keys()))
