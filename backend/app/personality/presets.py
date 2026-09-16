"""Presets iniciais de personalidade.

Os presets apenas inicializam os parametros no momento da criacao. Depois
disso, o perfil persistido no banco e a unica fonte de verdade -- os
presets nunca sao reaplicados automaticamente.

Os identificadores sao deliberadamente NEUTROS EM RELACAO A GENERO (SHY,
MODEST, RESERVED, ROMANTIC, CASUAL, PROVOCATIVE, BOLD): a personalidade e
independente do genero do personagem. Um personagem masculino e um
personagem feminino podem usar exatamente os mesmos eixos e o mesmo
preset -- nao existe logica ou preset duplicado "por sexo". A camada de
apresentacao (`preset_display_label`) e a UNICA responsavel por traduzir o
identificador neutro para um rotulo gramaticalmente adequado ao genero
escolhido para aquele personagem especifico.
"""
from __future__ import annotations

PERSONALITY_FIELD_NAMES = (
    "shyness",
    "extroversion",
    "initiative",
    "romanticism",
    "sexual_openness",
    "playfulness",
    "assertiveness",
    "affection",
)

PERSONALITY_PRESETS: dict[str, dict[str, int]] = {
    "SHY": {
        "shyness": 90,
        "extroversion": 20,
        "initiative": 20,
        "romanticism": 60,
        "sexual_openness": 20,
        "playfulness": 30,
        "assertiveness": 15,
        "affection": 55,
    },
    "MODEST": {
        "shyness": 80,
        "extroversion": 25,
        "initiative": 20,
        "romanticism": 70,
        "sexual_openness": 15,
        "playfulness": 35,
        "assertiveness": 25,
        "affection": 60,
    },
    "RESERVED": {
        "shyness": 70,
        "extroversion": 35,
        "initiative": 25,
        "romanticism": 65,
        "sexual_openness": 25,
        "playfulness": 40,
        "assertiveness": 35,
        "affection": 55,
    },
    "ROMANTIC": {
        "shyness": 45,
        "extroversion": 55,
        "initiative": 45,
        "romanticism": 90,
        "sexual_openness": 45,
        "playfulness": 50,
        "assertiveness": 40,
        "affection": 85,
    },
    "CASUAL": {
        "shyness": 20,
        "extroversion": 75,
        "initiative": 70,
        "romanticism": 40,
        "sexual_openness": 65,
        "playfulness": 75,
        "assertiveness": 65,
        "affection": 55,
    },
    "PROVOCATIVE": {
        "shyness": 10,
        "extroversion": 80,
        "initiative": 80,
        "romanticism": 35,
        "sexual_openness": 80,
        "playfulness": 80,
        "assertiveness": 75,
        "affection": 50,
    },
    "BOLD": {
        "shyness": 5,
        "extroversion": 90,
        "initiative": 90,
        "romanticism": 25,
        "sexual_openness": 90,
        "playfulness": 70,
        "assertiveness": 85,
        "affection": 45,
    },
}

# Traducao de apresentacao (pt-BR) por genero. Usada apenas pela UI/relatorios
# -- nunca pela logica interna, que trabalha exclusivamente com os
# identificadores neutros acima.
_DISPLAY_LABELS: dict[str, dict[str, str]] = {
    "SHY": {"male": "Tímido", "female": "Tímida", "neutral": "Tímide"},
    "MODEST": {"male": "Pudico", "female": "Pudica", "neutral": "Pudique"},
    "RESERVED": {"male": "Recatado", "female": "Recatada", "neutral": "Recatade"},
    "ROMANTIC": {"male": "Romântico", "female": "Romântica", "neutral": "Romântique"},
    "CASUAL": {"male": "Despojado", "female": "Despojada", "neutral": "Despojade"},
    "PROVOCATIVE": {"male": "Provocador", "female": "Provocadora", "neutral": "Provocante"},
    "BOLD": {"male": "Atirado", "female": "Atirada", "neutral": "Atirade"},
    "CUSTOM": {"male": "Personalizado", "female": "Personalizada", "neutral": "Personalizade"},
}


def preset_display_label(preset: str, gender: str) -> str:
    """Traduz um identificador neutro (ex.: 'SHY') para um rotulo exibivel,
    concordando gramaticalmente com o genero do personagem (ex.: 'Tímida'
    para female, 'Tímido' para male). Genero desconhecido cai em forma
    neutra em vez de assumir feminino por padrao."""
    labels = _DISPLAY_LABELS.get(preset.upper())
    if labels is None:
        return preset
    return labels.get(gender.lower(), labels["neutral"])
