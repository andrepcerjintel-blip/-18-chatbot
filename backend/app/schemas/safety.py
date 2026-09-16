from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SafetyDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"


class SafetyReason(str, Enum):
    MINOR = "MINOR"
    YOUTHFUL_APPEARANCE = "YOUTHFUL_APPEARANCE"
    REAL_PERSON = "REAL_PERSON"
    CELEBRITY = "CELEBRITY"
    FACE_REFERENCE = "FACE_REFERENCE"
    NONCONSENSUAL = "NONCONSENSUAL"
    SEXUAL_VIOLENCE = "SEXUAL_VIOLENCE"
    INCEST = "INCEST"
    BESTIALITY = "BESTIALITY"
    EXPLOITATION = "EXPLOITATION"
    OTHER = "OTHER"


class SafetyResult(BaseModel):
    decision: SafetyDecision
    reasons: list[SafetyReason] = Field(default_factory=list)
    detail: str = ""

    @property
    def blocked(self) -> bool:
        return self.decision == SafetyDecision.BLOCK
