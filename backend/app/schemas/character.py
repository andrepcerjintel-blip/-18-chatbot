from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

MIN_CHARACTER_AGE = 21

# Suportado desde o MVP; extensivel no futuro. Nunca assumir "female" como
# padrao -- CharacterCreate.gender e obrigatorio, sem valor default.
SUPPORTED_GENDERS = ("male", "female")
GenderLiteral = Literal["male", "female"]


class PersonalityPreset(str, Enum):
    """Identificadores NEUTROS EM RELACAO A GENERO. A personalidade e
    independente do genero do personagem; a UI traduz o identificador para
    um rotulo gramaticalmente adequado (ver app.personality.preset_display_label)
    apenas na camada de apresentacao, nunca na logica interna."""

    SHY = "SHY"
    MODEST = "MODEST"
    RESERVED = "RESERVED"
    ROMANTIC = "ROMANTIC"
    CASUAL = "CASUAL"
    PROVOCATIVE = "PROVOCATIVE"
    BOLD = "BOLD"
    CUSTOM = "CUSTOM"


class PersonalitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preset: PersonalityPreset = PersonalityPreset.CUSTOM
    shyness: int = Field(default=50, ge=0, le=100)
    extroversion: int = Field(default=50, ge=0, le=100)
    initiative: int = Field(default=50, ge=0, le=100)
    romanticism: int = Field(default=50, ge=0, le=100)
    sexual_openness: int = Field(default=50, ge=0, le=100)
    playfulness: int = Field(default=50, ge=0, le=100)
    assertiveness: int = Field(default=50, ge=0, le=100)
    affection: int = Field(default=50, ge=0, le=100)


class CharacterCreate(BaseModel):
    """Payload de criacao. `age` deve ser >=21 e `synthetic` e sempre True
    (nao aceito do cliente para evitar qualquer tentativa de burlar).

    `gender` e OBRIGATORIO e sem valor default: o sistema nunca presume
    "female" (nem nenhum outro genero) quando o campo esta ausente -- o
    cliente deve declarar explicitamente `male` ou `female`.

    `identity_origin` e `real_person_reference` propositalmente NAO
    existem aqui: sao campos protegidos, controlados exclusivamente pelo
    servidor (ver Character.PROTECTED_FIELDS)."""

    name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=MIN_CHARACTER_AGE, le=120)
    gender: GenderLiteral
    appearance: str = ""
    hair: str = ""
    eyes: str = ""
    skin: str = ""
    height: str = ""
    body_description: str = ""
    distinctive_features: str = ""
    visual_identity_reference: str = ""
    personality_preset: Optional[PersonalityPreset] = None
    personality: Optional[PersonalitySchema] = None

    @field_validator("age")
    @classmethod
    def enforce_min_age(cls, v: int) -> int:
        if v < MIN_CHARACTER_AGE:
            raise ValueError(f"age must be >= {MIN_CHARACTER_AGE}")
        return v


class CharacterUpdate(BaseModel):
    """Campos permitidos em PATCH administrativo. Propositalmente NAO inclui
    id, age, synthetic ou created_at: essas propriedades sao protegidas e
    imutaveis apos a criacao, inclusive nesta rota administrativa."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    gender: Optional[GenderLiteral] = None
    appearance: Optional[str] = None
    hair: Optional[str] = None
    eyes: Optional[str] = None
    skin: Optional[str] = None
    height: Optional[str] = None
    body_description: Optional[str] = None
    distinctive_features: Optional[str] = None
    visual_identity_reference: Optional[str] = None


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    age: int
    synthetic: Literal[True]
    gender: GenderLiteral
    appearance: str
    hair: str
    eyes: str
    skin: str
    height: str
    body_description: str
    distinctive_features: str
    visual_identity_reference: str
    identity_origin: str
    real_person_reference: Optional[str] = None
    created_at: datetime
    personality: PersonalitySchema
