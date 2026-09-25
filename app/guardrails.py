"""Garde-fous de sortie : vérifie en code que la réponse du LLM respecte ses sources.

Le prompt système demande déjà de citer chaque affirmation, mais une consigne n'est
pas une garantie. Ici on contrôle, phrase par phrase et sans appel LLM :
- que chaque article cité fait bien partie des passages retrouvés ;
- que chaque nombre (montant, taux, date) figure dans les passages cités, ou dans
  la question elle-même.
Une phrase qui échoue est retirée. S'il ne reste aucune phrase sourcée, la réponse
devient « Je ne sais pas. » (règle non négociable n° 1 du CLAUDE.md).
"""
import re

DONT_KNOW = "Je ne sais pas."

CITATION_PATTERN = re.compile(r"\[(Article premier|Art\.\s*\d+)\]", re.IGNORECASE)

# Un nombre avec d'éventuels séparateurs de milliers (espace, espace insécable ou
# point) et une partie décimale à virgule ou à point : 52 560 000 000 ; 3,5 ; 0.005.
NUMBER_PATTERN = re.compile(r"\d{1,3}(?:[   .]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")

# Découpe en phrases sans casser « Art. 2 » : on ne coupe qu'avant une majuscule,
# un guillemet ou une puce, jamais avant un chiffre.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀÂÉÈÊÎÔÛÇ«\-*•])")


def normalize_article(article: str) -> str:
    # Le PDF source contient parfois des doubles espaces (« Art.  4 »).
    return re.sub(r"\s+", " ", article.strip()).lower()


def normalize_number(raw: str) -> str:
    digits = re.sub(r"[   ]", "", raw)
    # Un point suivi d'exactement 3 chiffres est un séparateur de milliers (1.500.000).
    digits = re.sub(r"\.(?=\d{3}(?!\d))", "", digits)
    digits = digits.replace(",", ".")
    if "." in digits:
        digits = digits.rstrip("0").rstrip(".")
    return digits


def numbers_in(text: str) -> set[str]:
    return {normalize_number(m) for m in NUMBER_PATTERN.findall(text)}


def check_sentence(sentence: str, passages_by_article: dict[str, list[str]], question_numbers: set[str]) -> dict | None:
    """Renvoie la raison du rejet, ou None si la phrase est justifiée par ses sources."""
    cited = [normalize_article(c) for c in CITATION_PATTERN.findall(sentence)]
    # Les numéros d'articles entre crochets ne sont pas des affirmations chiffrées, et
    # reprendre un nombre de la question (« pour 2026 ») n'affirme rien de nouveau.
    numbers = numbers_in(CITATION_PATTERN.sub("", sentence)) - question_numbers

    unknown = [c for c in cited if c not in passages_by_article]
    if unknown:
        return {"reason": "citation_hors_sources", "detail": unknown}
    if numbers and not cited:
        return {"reason": "chiffre_non_cite", "detail": sorted(numbers)}

    source_numbers = set().union(*(numbers_in(t) for c in cited for t in passages_by_article[c]))
    unsupported = sorted(numbers - source_numbers)
    if unsupported:
        return {"reason": "chiffre_absent_des_sources", "detail": unsupported}
    return None


def validate_answer(answer: str, passages: list[dict], question: str) -> tuple[str, dict]:
    """Retourne (réponse filtrée, rapport des phrases retirées et pourquoi)."""
    report = {"removed": [], "fallback_dont_know": False}
    if answer.strip() == DONT_KNOW:
        return DONT_KNOW, report

    passages_by_article: dict[str, list[str]] = {}
    for p in passages:
        passages_by_article.setdefault(normalize_article(p["article"]), []).append(p["texte"])
    question_numbers = numbers_in(question)

    kept_lines = []
    kept_cited = 0
    # Ligne par ligne pour préserver la mise en forme (paragraphes, listes à puces).
    for line in answer.splitlines():
        if not line.strip():
            kept_lines.append(line)
            continue
        kept_sentences = []
        for sentence in SENTENCE_SPLIT.split(line):
            rejection = check_sentence(sentence, passages_by_article, question_numbers)
            if rejection:
                report["removed"].append({"sentence": sentence, **rejection})
                continue
            kept_sentences.append(sentence)
            if CITATION_PATTERN.search(sentence):
                kept_cited += 1
        if kept_sentences:
            kept_lines.append(" ".join(kept_sentences))

    if kept_cited == 0:
        report["fallback_dont_know"] = True
        return DONT_KNOW, report
    return "\n".join(kept_lines).strip(), report
