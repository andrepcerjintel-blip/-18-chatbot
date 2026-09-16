"""Character Manager.

Unico ponto de escrita para a entidade Character/PersonalityProfile.
Garante as invariantes:
  - age >= MIN_CHARACTER_AGE (21)
  - synthetic == True sempre
  - id / created_at imutaveis
  - campos protegidos nunca aceitam alteracao vinda de texto de conversa

O Conversation Engine NUNCA deve tocar diretamente no ORM de Character;
toda mutacao passa por aqui, e apenas via CharacterUpdate (schema que ja
exclui os campos protegidos em tempo de tipagem).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.character.presets import PERSONALITY_PRESETS
from app.logging_config import logger
from app.models.character import MIN_CHARACTER_AGE, Character
from app.models.personality import PersonalityProfile
from app.schemas.character import CharacterCreate, CharacterUpdate


class ProtectedFieldError(Exception):
    """Levantado quando uma tentativa de alterar um campo protegido ocorre."""


class CharacterManager:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: CharacterCreate) -> Character:
        if payload.age < MIN_CHARACTER_AGE:
            # Defesa em profundidade: o schema ja bloqueia isso, mas
            # nunca confiamos em uma unica camada de validacao.
            raise ValueError(f"age must be >= {MIN_CHARACTER_AGE}")

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
        )
        self.db.add(character)
        self.db.flush()

        params = dict.fromkeys(
            (
                "shyness",
                "extroversion",
                "initiative",
                "romanticism",
                "sexual_openness",
                "playfulness",
                "assertiveness",
                "affection",
            ),
            50,
        )
        preset_name = "custom"
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
