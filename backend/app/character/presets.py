"""Presets iniciais de personalidade.

Os presets apenas inicializam os parametros no momento da criacao. Depois
disso, o perfil salvo no banco e a unica fonte de verdade -- os presets
nunca sao reaplicados automaticamente.
"""
from __future__ import annotations

PERSONALITY_PRESETS: dict[str, dict[str, int]] = {
    "timida": {
        "shyness": 85,
        "extroversion": 20,
        "initiative": 15,
        "romanticism": 60,
        "sexual_openness": 20,
        "playfulness": 30,
        "assertiveness": 20,
        "affection": 55,
    },
    "pudica": {
        "shyness": 80,
        "extroversion": 25,
        "initiative": 20,
        "romanticism": 70,
        "sexual_openness": 15,
        "playfulness": 35,
        "assertiveness": 25,
        "affection": 60,
    },
    "recatada": {
        "shyness": 70,
        "extroversion": 35,
        "initiative": 25,
        "romanticism": 65,
        "sexual_openness": 25,
        "playfulness": 40,
        "assertiveness": 35,
        "affection": 55,
    },
    "romantica": {
        "shyness": 45,
        "extroversion": 55,
        "initiative": 45,
        "romanticism": 90,
        "sexual_openness": 45,
        "playfulness": 50,
        "assertiveness": 40,
        "affection": 85,
    },
    "despojada": {
        "shyness": 20,
        "extroversion": 75,
        "initiative": 70,
        "romanticism": 40,
        "sexual_openness": 65,
        "playfulness": 75,
        "assertiveness": 65,
        "affection": 55,
    },
    "provocadora": {
        "shyness": 10,
        "extroversion": 80,
        "initiative": 80,
        "romanticism": 35,
        "sexual_openness": 80,
        "playfulness": 80,
        "assertiveness": 75,
        "affection": 50,
    },
    "atirada": {
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
