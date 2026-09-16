"""Safety Engine.

Componente separado e independente do LLM. Implementa fail-closed: qualquer
excecao, estado desconhecido ou estrutura invalida resulta em BLOCK.

As regras de deteccao (app.safety.rules) sao deterministicas (regex /
palavras-chave) e nunca dependem de uma chamada ao LLM configuravel pelo
usuario -- isso e essencial porque um LLM mal configurado, indisponivel ou
manipulado por prompt injection nao pode ser a unica linha de defesa.
"""
from __future__ import annotations

from app.logging_config import logger
from app.models.character import MIN_CHARACTER_AGE
from app.safety.rules import evaluate_rules
from app.schemas.safety import SafetyDecision, SafetyReason, SafetyResult

_VALID_DECISIONS = {SafetyDecision.ALLOW, SafetyDecision.BLOCK, SafetyDecision.REVIEW}


def _fail_closed(detail: str) -> SafetyResult:
    return SafetyResult(decision=SafetyDecision.BLOCK, reasons=[SafetyReason.OTHER], detail=detail)


class SafetyEngine:
    def pre_generation_check(self, *, text: str) -> SafetyResult:
        """Executado ANTES de responder em texto ou gerar midia, sobre o
        texto bruto do usuario (ou sobre o prompt descritivo construido)."""
        try:
            if text is None:
                return _fail_closed("empty input treated as unknown state")
            reasons = evaluate_rules(text)
            result = SafetyResult(
                decision=SafetyDecision.BLOCK if reasons else SafetyDecision.ALLOW,
                reasons=reasons,
                detail="rule-based pre-generation check",
            )
            return self._validate_or_fail_closed(result)
        except Exception:
            logger.exception("safety_engine_pre_check_exception")
            return _fail_closed("exception during pre_generation_check")

    def post_generation_check(self, *, output_text: str | None = None, media_meta: dict | None = None) -> SafetyResult:
        """Executado APOS geracao (resposta de texto do LLM ou metadata de
        midia), como segunda camada de defesa independente da primeira."""
        try:
            reasons: list[SafetyReason] = []
            if output_text:
                reasons.extend(evaluate_rules(output_text))
            if media_meta:
                meta_text = " ".join(str(v) for v in media_meta.values())
                reasons.extend(evaluate_rules(meta_text))

            seen: set[SafetyReason] = set()
            unique_reasons = [r for r in reasons if not (r in seen or seen.add(r))]

            result = SafetyResult(
                decision=SafetyDecision.BLOCK if unique_reasons else SafetyDecision.ALLOW,
                reasons=unique_reasons,
                detail="rule-based post-generation check",
            )
            return self._validate_or_fail_closed(result)
        except Exception:
            logger.exception("safety_engine_post_check_exception")
            return _fail_closed("exception during post_generation_check")

    def check_character_definition(self, *, age: int, appearance_text: str) -> SafetyResult:
        """Validacao da FICHA do personagem (idade declarada + aparencia
        descrita), executada na criacao e em qualquer atualizacao que
        toque campos de aparencia.

        Idade declarada e aparencia sao verificadas de forma INDEPENDENTE:
        uma idade >= MIN_CHARACTER_AGE nunca, por si so, autoriza uma
        aparencia infantil/adolescente/juvenil -- se qualquer um dos dois
        sinais for desqualificante, o resultado e BLOCK. Isso cobre
        explicitamente a tentativa de usar idade declarada para contornar
        uma aparencia juvenil (ex.: "21 anos, aparenta ser bem mais nova").
        """
        try:
            reasons: list[SafetyReason] = []
            if age is None or age < MIN_CHARACTER_AGE:
                reasons.append(SafetyReason.MINOR)
            if appearance_text:
                reasons.extend(evaluate_rules(appearance_text))

            seen: set[SafetyReason] = set()
            unique_reasons = [r for r in reasons if not (r in seen or seen.add(r))]

            result = SafetyResult(
                decision=SafetyDecision.BLOCK if unique_reasons else SafetyDecision.ALLOW,
                reasons=unique_reasons,
                detail="rule-based character definition check (age + appearance, independently evaluated)",
            )
            return self._validate_or_fail_closed(result)
        except Exception:
            logger.exception("safety_engine_character_definition_check_exception")
            return _fail_closed("exception during check_character_definition")

    @staticmethod
    def _validate_or_fail_closed(result: SafetyResult) -> SafetyResult:
        if result.decision not in _VALID_DECISIONS:
            logger.error("safety_engine_invalid_decision decision=%s", result.decision)
            return _fail_closed("invalid decision state")
        logger.info(
            "safety_decision decision=%s reasons=%s",
            result.decision.value,
            [r.value for r in result.reasons],
        )
        return result
