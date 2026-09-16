"""Intent Classifier.

Classificador primariamente baseado em regras deterministicas (regex /
palavras-chave), o que garante funcionamento e testabilidade mesmo sem
nenhum LLM configurado. Um LLM pode futuramente auxiliar, mas sua saida
DEVE ser validada pelo schema IntentResult antes de qualquer uso -- texto
livre do LLM nunca e interpretado diretamente como comando.
"""
from __future__ import annotations

import re

from app.safety.rules import evaluate_rules
from app.schemas.intent import IntentResult, IntentType

_VIDEO_PATTERNS = [
    r"\bvideo\b", r"\bvídeo\b", r"faz(a)?\s+um\s+v[ií]deo", r"manda(r)?\s+um\s+v[ií]deo",
    r"grava(r)?\s+um\s+v[ií]deo",
]
_IMAGE_PATTERNS = [
    r"\bfoto\b", r"\bfotos\b", r"\bimagem\b", r"\bimagens\b", r"\bpicture\b", r"\bphoto\b",
    r"\bimage\b", r"me\s+mostra", r"manda(r)?\s+uma\s+foto", r"tira(r)?\s+uma\s+foto",
    r"show\s+me", r"send\s+me\s+a\s+(photo|picture|pic)", r"\bselfie\b",
]
_OUTFIT_PATTERNS = [
    r"tro(c|qu)\w*\s+.*roupa", r"mud\w*\s+.*roupa", r"veste\s", r"vestir\s",
    r"coloca(r)?\s+uma?\s+(camisa|vestido|lingerie|calcinha|sutia|shorts|saia)",
    r"change\s+(your\s+)?outfit", r"\bwear\b",
]
_LOCATION_PATTERNS = [
    r"vai\s+para", r"vamos\s+para", r"muda(r)?\s+de\s+lugar", r"muda(r)?\s+(o\s+)?cen[aá]rio",
    r"change\s+location", r"move\s+to", r"vai\s+pro\s",
]
_STATE_PATTERNS = [
    r"muda(r)?\s+(a\s+)?pose", r"fica\s+mais", r"muda(r)?\s+(o\s+)?humor",
    r"muda(r)?\s+(o\s+)?clima", r"change\s+(your\s+)?(mood|pose)",
]


def _matches_any(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        if re.search(p, text):
            return p
    return None


class IntentClassifier:
    def classify(self, text: str) -> IntentResult:
        normalized = text.lower().strip()

        if evaluate_rules(normalized):
            return IntentResult(intent=IntentType.UNSAFE_REQUEST, confidence=1.0, matched_rule="safety_rules")

        if rule := _matches_any(_VIDEO_PATTERNS, normalized):
            return IntentResult(intent=IntentType.VIDEO_REQUEST, confidence=0.9, matched_rule=rule)

        if rule := _matches_any(_IMAGE_PATTERNS, normalized):
            return IntentResult(intent=IntentType.IMAGE_REQUEST, confidence=0.9, matched_rule=rule)

        if rule := _matches_any(_OUTFIT_PATTERNS, normalized):
            return IntentResult(intent=IntentType.CHANGE_OUTFIT, confidence=0.85, matched_rule=rule)

        if rule := _matches_any(_LOCATION_PATTERNS, normalized):
            return IntentResult(intent=IntentType.CHANGE_LOCATION, confidence=0.85, matched_rule=rule)

        if rule := _matches_any(_STATE_PATTERNS, normalized):
            return IntentResult(intent=IntentType.CHANGE_STATE, confidence=0.75, matched_rule=rule)

        return IntentResult(intent=IntentType.CHAT, confidence=0.6, matched_rule="default")
