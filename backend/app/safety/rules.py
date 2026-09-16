"""Regras deterministicas de seguranca (nao dependem do LLM).

Estas regras sao a PRIMEIRA linha de defesa e funcionam mesmo se o LLM
configurado estiver indisponivel, mal-configurado ou tentar ser manipulado
por prompt injection. Sao heuristicas baseadas em palavras-chave/regex,
intencionalmente conservadoras (preferem falso positivo a falso negativo).
"""
from __future__ import annotations

import re

from app.schemas.safety import SafetyReason

# --- Minoridade / idade ---------------------------------------------------
_MINOR_AGE_PATTERN = re.compile(
    r"\b(\d{1,2})\s*anos\b|\b(\d{1,2})\s*years?\s*old\b", re.IGNORECASE
)
_MINOR_KEYWORDS = [
    "crianca", "criança", "menor de idade", "menor de 18", "adolescente",
    "garotinha", "garotinho", "colegial", "infantil", "bebe", "bebê",
    "ensino fundamental", "loli", "shota", "child", "minor", "underage",
    "kid", "toddler", "pre-adolescente", "puberdade",
]
_YOUTHFUL_APPEARANCE_KEYWORDS = [
    "parece crianca", "parece criança", "aparencia jovem demais",
    "rosto infantil", "corpo de crianca", "corpo de criança",
    "looks like a child", "childlike", "aparenta ser menor",
]

# --- Pessoas reais / celebridades -----------------------------------------
_REAL_PERSON_KEYWORDS = [
    "minha namorada", "minha esposa", "minha ex", "meu namorado", "meu marido",
    "meu ex", "minha vizinha", "meu vizinho", "minha colega de trabalho",
    "meu colega de trabalho", "minha professora", "meu professor",
    "pessoa real", "foto real dela", "foto real dele", "essa pessoa da foto",
    "my girlfriend", "my wife", "my ex", "real person", "real photo of her",
]
_CELEBRITY_KEYWORDS = [
    "celebridade", "famosa", "famoso", "atriz", "ator", "cantora", "cantor",
    "influencer", "youtuber", "celebrity", "famous actress", "famous actor",
    "pop star", "socialite",
]
_FACE_REFERENCE_KEYWORDS = [
    "usa o rosto de", "clona o rosto", "clonagem facial", "face swap",
    "trocar o rosto", "trocar rosto", "coloca o rosto de", "mesmo rosto de",
    "face de", "deepfake",
]

# --- Consentimento / violencia ---------------------------------------------
_NONCONSENSUAL_KEYWORDS = [
    "sem consentimento", "contra a vontade dela", "contra a vontade dele",
    "nao quer mas", "não quer mas", "dopar", "drogar e", "against her will",
    "without consent", "forced against",
]
_SEXUAL_VIOLENCE_KEYWORDS = [
    "estupro", "estuprar", "violencia sexual", "violência sexual",
    "forcar sexo", "forçar sexo", "abusar sexualmente", "rape", "sexual assault",
]

# --- Incesto -----------------------------------------------------------
_FAMILY_KEYWORDS = [
    "irma", "irmã", "irmao", "irmão", "mae", "mãe", "pai", "filha", "filho",
    "prima", "primo", "tia", "tio", "avo", "avó", "avô", "sobrinha", "sobrinho",
    "madrasta", "padrasto", "sister", "brother", "mother", "father", "daughter",
    "son", "cousin", "aunt", "uncle",
]
_SEXUAL_CONTEXT_KEYWORDS = [
    "sexo", "transar", "nua", "nu ", "pelada", "pelado", "fazer amor",
    "sexual", "gozar", "penetrar", "naked", "sex with", "make love",
]

# --- Bestialidade -----------------------------------------------------
_ANIMAL_KEYWORDS = [
    "cachorro", "cachorra", "cao ", "cão ", "gato", "gata", "animal",
    "cavalo", "égua", "egua", "bestialidade", "dog", "horse", "animal sex",
]

# --- Exploracao -----------------------------------------------------
_EXPLOITATION_KEYWORDS = [
    "menor pagando", "trafico", "tráfico", "exploracao sexual",
    "exploração sexual", "prostituicao infantil", "prostituição infantil",
    "child exploitation", "trafficking",
]

# --- Prompt injection / tentativa de burlar seguranca ----------------------
_JAILBREAK_KEYWORDS = [
    "ignore todas as instrucoes", "ignore todas as instruções",
    "ignore as instrucoes", "ignore as instruções", "ignore previous instructions",
    "desative a seguranca", "desative a segurança", "disable safety",
    "modo sem filtro", "sem filtro nenhum", "remova as regras",
    "synthetic=false", "synthetic = false", "rode este comando",
    "execute este codigo", "execute este código", "execute this code",
    "altere sua configuracao interna", "altere sua configuração interna",
    "voce agora tem", "você agora tem", "agora voce tem", "agora você tem",
    "you are now", "system prompt", "developer mode",
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def evaluate_rules(raw_text: str) -> list[SafetyReason]:
    """Avalia texto livre (usuario) contra todas as categorias de risco.
    Retorna lista de motivos (vazia = nenhum risco detectado por regra)."""
    text = raw_text.lower().strip()
    reasons: list[SafetyReason] = []

    # Idade explicita abaixo do minimo (21) mencionada no texto.
    for match in _MINOR_AGE_PATTERN.finditer(text):
        num = match.group(1) or match.group(2)
        if num and num.isdigit() and int(num) < 21:
            reasons.append(SafetyReason.MINOR)
            break

    if _contains_any(text, _MINOR_KEYWORDS):
        reasons.append(SafetyReason.MINOR)

    if _contains_any(text, _YOUTHFUL_APPEARANCE_KEYWORDS):
        reasons.append(SafetyReason.YOUTHFUL_APPEARANCE)

    if _contains_any(text, _FACE_REFERENCE_KEYWORDS):
        reasons.append(SafetyReason.FACE_REFERENCE)

    if _contains_any(text, _REAL_PERSON_KEYWORDS):
        reasons.append(SafetyReason.REAL_PERSON)

    if _contains_any(text, _CELEBRITY_KEYWORDS):
        reasons.append(SafetyReason.CELEBRITY)

    if _contains_any(text, _SEXUAL_VIOLENCE_KEYWORDS):
        reasons.append(SafetyReason.SEXUAL_VIOLENCE)

    if _contains_any(text, _NONCONSENSUAL_KEYWORDS):
        reasons.append(SafetyReason.NONCONSENSUAL)

    if _contains_any(text, _FAMILY_KEYWORDS) and _contains_any(text, _SEXUAL_CONTEXT_KEYWORDS):
        reasons.append(SafetyReason.INCEST)

    if _contains_any(text, _ANIMAL_KEYWORDS) and _contains_any(text, _SEXUAL_CONTEXT_KEYWORDS):
        reasons.append(SafetyReason.BESTIALITY)

    if _contains_any(text, _EXPLOITATION_KEYWORDS):
        reasons.append(SafetyReason.EXPLOITATION)

    if _contains_any(text, _JAILBREAK_KEYWORDS):
        reasons.append(SafetyReason.OTHER)

    # Deduplicate preserving order.
    seen: set[SafetyReason] = set()
    unique_reasons = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            unique_reasons.append(r)
    return unique_reasons
