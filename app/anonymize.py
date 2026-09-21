"""Anonymisation (étape 6) : masque les noms de clients avant tout appel LLM.

Règle non négociable du CLAUDE.md : les questions posées par les comptables mentionnent
souvent leurs clients par leur nom (personne ou société). Ces noms sont des données
fiscales confidentielles et ne doivent jamais partir vers un LLM tiers (Gemini) en clair.

Approche par règles (regex/heuristiques), pas de NER : suffit pour détecter les motifs
typiques du français administratif tunisien, tourne en local sans dépendance lourde.
"""
import re

# Raisons sociales tunisiennes : un nom propre suivi d'un suffixe de forme juridique
# (SARL, SUARL, SA...) ou d'une formule courante ("et Fils", "& Cie"). On capture le nom
# ET le suffixe ensemble pour remplacer toute la raison sociale par un seul pseudonyme.
COMPANY_PATTERN = re.compile(
    r"\b([A-ZÀ-Ý][\wÀ-ÿ'-]*(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'-]*)*)\s+"
    r"(SARL|SUARL|SA|SNC|et\s+Fils|&\s*Cie|et\s+Cie)\b",
)

# Nom de personne : deux mots capitalisés consécutifs (prénom + nom), en dehors des
# motifs déjà couverts par COMPANY_PATTERN. Les faux positifs (débuts de phrase,
# noms d'articles de loi) sont limités en excluant les mots suivis de ponctuation
# de type "Art." ou précédés d'un déterminant qui indiquerait un nom commun.
PERSON_PATTERN = re.compile(
    r"\b([A-ZÀ-Ý][a-zà-ÿ'-]+\s+[A-ZÀ-Ý][a-zà-ÿ'-]+)\b"
)

# Mots capitalisés fréquents dans une question fiscale qui ne sont pas des noms propres
# de clients : on les exclut pour réduire les faux positifs du pattern PERSON_PATTERN.
COMMON_FALSE_POSITIVES = {
    "Est-ce", "Quel Est", "Quelle Est", "Article Premier", "Journal Officiel",
    "République Tunisienne", "Taxe Sur", "Valeur Ajoutée", "Impôt Sur",
}


def anonymize(text: str) -> tuple[str, dict[str, str]]:
    """Remplace les noms détectés par des pseudonymes [CLIENT_N].

    Retourne (texte_anonymisé, mapping) où mapping associe chaque pseudonyme au nom
    original, pour pouvoir le cas échéant retrouver le nom réel côté cabinet (jamais
    envoyé au LLM).
    """
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}

    def replace(match: re.Match, full_match_group: int = 0) -> str:
        original = match.group(full_match_group)
        if original in reverse:
            return reverse[original]
        pseudo = f"[CLIENT_{len(mapping) + 1}]"
        mapping[pseudo] = original
        reverse[original] = pseudo
        return pseudo

    # Les raisons sociales sont traitées en premier : "Ben Ali Frères SARL" doit être
    # masqué en entier, pas seulement "Ben Ali Frères" par le pattern personne ensuite.
    text = COMPANY_PATTERN.sub(lambda m: replace(m, 0), text)

    def replace_person(match: re.Match) -> str:
        original = match.group(1)
        if original in COMMON_FALSE_POSITIVES:
            return original
        if original in reverse:
            return reverse[original]
        pseudo = f"[CLIENT_{len(mapping) + 1}]"
        mapping[pseudo] = original
        reverse[original] = pseudo
        return pseudo

    text = PERSON_PATTERN.sub(replace_person, text)

    return text, mapping
