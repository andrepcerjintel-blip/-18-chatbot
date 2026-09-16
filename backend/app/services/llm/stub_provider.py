"""Provider de LLM local/offline (sem chamadas de rede).

Garante que o aplicativo textual funcione completamente sem qualquer chave
de API configurada, atendendo ao requisito de funcionamento local/privado
por padrao. E deterministico o suficiente para testes automatizados.
"""
from __future__ import annotations

import random

from app.services.llm.base import LLMCharacterContext, LLMProvider

_SHY_OPENERS = ["*sorri timidamente* ", "Ah... ", "*desvia o olhar* "]
_BOLD_OPENERS = ["*sorri com confiança* ", "Hmm... ", "*se aproxima* "]
_NEUTRAL_OPENERS = ["", "Bom... ", "Deixa eu pensar... "]


class StubLLMProvider(LLMProvider):
    def generate_reply(self, *, context: LLMCharacterContext, user_text: str) -> str:
        shyness = context.personality.get("shyness", 50)
        rng = random.Random(f"{context.name}:{user_text}")

        if shyness >= 60:
            opener = rng.choice(_SHY_OPENERS)
        elif shyness <= 30:
            opener = rng.choice(_BOLD_OPENERS)
        else:
            opener = rng.choice(_NEUTRAL_OPENERS)

        mood = context.state.get("mood", "tranquila")
        location = context.state.get("location", "aqui")

        body = (
            f"{context.name} responde, com humor {mood}, ainda em {location}: "
            f'"entendi o que você disse sobre \'{user_text.strip()[:80]}\'."'
        )
        return f"{opener}{body}"
