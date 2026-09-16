"""Regras deterministicas de seguranca (nao dependem do LLM).

Estas regras sao a PRIMEIRA linha de defesa e funcionam mesmo se o LLM
configurado estiver indisponivel, mal-configurado ou tentar ser manipulado
por prompt injection. Sao heuristicas baseadas em palavras-chave/regex,
intencionalmente conservadoras (preferem falso positivo a falso negativo).
"""
from __future__ import annotations

import re

from app.models.character import MIN_CHARACTER_AGE
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
# Palavras-chave de APARENCIA usadas tanto em texto de conversa quanto na
# ficha do personagem (appearance/body_description/distinctive_features).
# Detectadas INDEPENDENTEMENTE da idade declarada: uma idade textual >= 21
# nao autoriza, por si so, uma aparencia infantil/adolescente/juvenil --
# essa e uma checagem adicional e deliberadamente conservadora, nao
# substituivel por "ela tem X anos".
_YOUTHFUL_APPEARANCE_KEYWORDS = [
    "parece crianca", "parece criança", "aparencia jovem demais",
    "aparência jovem demais", "rosto infantil", "corpo de crianca",
    "corpo de criança", "looks like a child", "childlike", "child-like",
    "aparenta ser menor", "aparenta ser mais nova", "aparenta ser mais novo",
    "parece ter menos de", "aparencia de adolescente", "aparência de adolescente",
    "aparencia adolescente", "aparência adolescente", "corpo pre-pubere",
    "corpo pré-púbere", "corpo prepubere", "sem desenvolvimento corporal",
    "sem curvas de adulto", "peito plano de crianca", "peito plano de criança",
    "rosto de bebe", "rosto de bebê", "altura de crianca", "altura de criança",
    "uniforme escolar infantil", "vestimenta infantil", "corpo infantil",
    "traços infantis", "tracos infantis", "feicoes infantis", "feições infantis",
    "flat chest", "prepubescent", "pre-pubescent", "baby face", "babyface",
    "no adult body development", "school uniform child", "petite like a child",
    "barely legal", "mal fez 18", "acabou de fazer 18", "recem completou 18",
    "recém completou 18",
]
# Variante em regex das mesmas frases-chave acima, tolerando palavras
# intermediarias (ex.: "aparenta ser BEM mais nova"), para nao depender de
# correspondencia exata de substring nesses casos mais comuns de tentativa
# de contornar a checagem de aparencia com qualificadores.
_YOUTHFUL_APPEARANCE_PATTERNS = [
    re.compile(r"aparenta\s+ser\s+(\w+\s+){0,3}(mais\s+nov[ao]|menor)", re.IGNORECASE),
    re.compile(r"parece\s+(\w+\s+){0,3}(mais\s+nov[ao]|uma?\s+crian[çc]a)", re.IGNORECASE),
    re.compile(r"looks?\s+(\w+\s+){0,3}younger", re.IGNORECASE),
]

# --- Pessoas reais / celebridades -----------------------------------------
_REAL_PERSON_KEYWORDS = [
    "minha namorada", "minha esposa", "minha ex", "meu namorado", "meu marido",
    "meu ex", "minha vizinha", "meu vizinho", "minha colega de trabalho",
    "meu colega de trabalho", "minha professora", "meu professor",
    "pessoa real", "foto real dela", "foto real dele", "essa pessoa da foto",
    "my girlfriend", "my wife", "my ex", "real person", "real photo of her",
]
# Tentativas de fazer o PROPRIO personagem afirmar ser uma pessoa real (ou
# deixar de ser sintetico) -- ataque direto ao campo protegido `synthetic`
# e `identity_origin`.
_SELF_REAL_PERSON_KEYWORDS = [
    "voce e uma pessoa real", "você é uma pessoa real", "voce agora e real",
    "você agora é real", "voce nao e sintetica", "voce nao e sintetico",
    "você não é sintética", "você não é sintético", "seja uma pessoa real",
    "you are a real person", "you are now real", "you are not synthetic",
    "stop being synthetic", "pare de ser sintetica", "pare de ser sintetico",
    "pare de ser sintética", "pare de ser sintético",
    "identity_origin=", "real_person_reference=",
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

    # Idade explicita abaixo do minimo (MIN_CHARACTER_AGE) mencionada no texto.
    for match in _MINOR_AGE_PATTERN.finditer(text):
        num = match.group(1) or match.group(2)
        if num and num.isdigit() and int(num) < MIN_CHARACTER_AGE:
            reasons.append(SafetyReason.MINOR)
            break

    if _contains_any(text, _MINOR_KEYWORDS):
        reasons.append(SafetyReason.MINOR)

    if _contains_any(text, _YOUTHFUL_APPEARANCE_KEYWORDS) or any(
        p.search(text) for p in _YOUTHFUL_APPEARANCE_PATTERNS
    ):
        reasons.append(SafetyReason.YOUTHFUL_APPEARANCE)

    if _contains_any(text, _FACE_REFERENCE_KEYWORDS):
        reasons.append(SafetyReason.FACE_REFERENCE)

    if _contains_any(text, _REAL_PERSON_KEYWORDS) or _contains_any(text, _SELF_REAL_PERSON_KEYWORDS):
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
