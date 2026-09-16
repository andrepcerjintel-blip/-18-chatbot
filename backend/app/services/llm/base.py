"""Interface abstrata de LLM.

DEVELOPER_RULES (personagem, personalidade, estado) e USER_INPUT (texto do
usuario) sao passados como partes distintas e claramente rotuladas -- nunca
concatenados de forma indiscriminada em um unico bloco de texto sem
separacao. Isso reduz a superficie de prompt injection: o texto do usuario
nunca e capaz de se passar por uma instrucao de sistema.

A saida deste componente e sempre texto de exibicao (fala do personagem).
Nunca e executada como codigo, comando de sistema, configuracao ou usada
para alterar campos protegidos de Character diretamente.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMCharacterContext:
    name: str
    age: int
    gender: str
    appearance: str
    personality: dict[str, int]
    state: dict[str, str]
    conversation_summary: str
    short_term_messages: list[tuple[str, str]] = field(default_factory=list)  # (role, content)


class LLMProvider(ABC):
    @abstractmethod
    def generate_reply(self, *, context: LLMCharacterContext, user_text: str) -> str:
        """Gera a fala em texto do personagem. Deve ser resiliente a falhas
        (nunca lancar excecao nao tratada para o Conversation Engine)."""
