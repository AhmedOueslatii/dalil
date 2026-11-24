"""Outils de l'agent fiscal.

Chaque outil renvoie deux choses :
- `content` : ce que le LLM lit (dict JSON) ;
- `passages` : les éléments citables qui alimentent le garde-fou de sortie. Une phrase
  de la réponse finale ne survit que si l'article qu'elle cite et les chiffres qu'elle
  avance figurent dans ces passages (app/guardrails.py).

Un outil ne lève pas d'exception vers la boucle pour une erreur d'argument : il renvoie
{"erreur": ...} afin que le modèle corrige son appel au tour suivant.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Callable

from pydantic import ValidationError

from app.agent.llm import ToolSpec
from app.calculators import wealth_tax
from app.calculators.params import load_parameters
from app.guardrails import NUMBER_PATTERN, normalize_number
from app.search import hybrid_search

ASK_USER_TOOL = "demander_precisions"


@dataclass
class ToolOutput:
    content: dict
    passages: list[dict] = field(default_factory=list)


@dataclass
class Tool:
    spec: ToolSpec
    # (arguments du modèle, question anonymisée) → résultat. La question sert aux outils
    # qui doivent vérifier que le modèle n'invente pas leurs données d'entrée.
    handler: Callable[[dict, str], ToolOutput]


def search_texts(args: dict, question: str) -> ToolOutput:
    query = str(args.get("requete", "")).strip()
    if not query:
        return ToolOutput({"erreur": "Le paramètre « requete » est vide."})
    try:
        top_k = max(1, min(int(args.get("nombre") or 5), 8))
    except (TypeError, ValueError):
        return ToolOutput({"erreur": "« nombre » doit être un entier entre 1 et 8."})

    passages = hybrid_search(query, top_k=top_k)
    if not passages:
        return ToolOutput({"passages": [], "note": "Aucun passage trouvé. Reformule avec d'autres termes juridiques."})
    return ToolOutput(
        content={"passages": [{"article": p["article"], "document": p["titre"], "texte": p["texte"]} for p in passages]},
        passages=[{"article": p["article"], "titre": p["titre"], "source": p["source"], "texte": p["texte"]} for p in passages],
    )


# « 6 MTND », « 2,5 millions », « 500 mille » : montants écrits avec un multiplicateur.
SCALED_AMOUNT = re.compile(rf"({NUMBER_PATTERN.pattern})\s*(milliards?|millions?|mille|mtnd|mdt|md|m)\b", re.IGNORECASE)
SCALES = {"milliard": 10**9, "million": 10**6, "mille": 10**3, "mtnd": 10**6, "mdt": 10**6, "md": 10**6, "m": 10**6}


def amounts_in(text: str) -> set[Decimal]:
    amounts = {Decimal(normalize_number(n)) for n in NUMBER_PATTERN.findall(text)}
    for number, unit in SCALED_AMOUNT.findall(text):
        amounts.add(Decimal(normalize_number(number)) * SCALES[unit.lower().rstrip("s")])
    return amounts


def compute_wealth_tax(args: dict, question: str) -> ToolOutput:
    try:
        payload = wealth_tax.WealthTaxInput.model_validate(args)
    except ValidationError as exc:
        return ToolOutput({"erreur": f"Données invalides : {exc.errors(include_url=False)}"})

    # Le détail du calcul devient un passage citable : sans ce contrôle, une valeur
    # inventée par le modèle passerait le garde-fou avec une citation [Art. 88].
    allowed = amounts_in(question)
    values = [a.value_tnd for a in payload.assets] + [payload.deductible_debts_tnd]
    invented = sorted({str(v) for v in values if v and Decimal(str(v)) not in allowed})
    if invented:
        return ToolOutput({"erreur": (
            f"Montant(s) absent(s) de la question : {', '.join(invented)}. N'invente aucune "
            "valeur : appelle demander_precisions pour l'obtenir du comptable."
        )})

    params, sources = load_parameters(wealth_tax.CALCULATOR, date.today())
    if any(key not in params for key in wealth_tax.REQUIRED_PARAMS):
        return ToolOutput({"erreur": "Paramètres de calcul non disponibles pour la date du jour."})

    response = wealth_tax.build_response(wealth_tax.compute(payload, params), payload.resident_in_tunisia, sources)
    # Le détail du calcul devient un passage citable sous l'article qui le fonde : le
    # garde-fou acceptera les montants calculés par le code, et eux seuls.
    lines = [f"{s['label']} : {s['amount']}" for s in response["steps"]] + [f"Impôt total : {response['total']}"]
    calc_passage = {
        "article": wealth_tax.ARTICLE,
        "titre": "Calcul Dalil : impôt sur la fortune",
        "source": "calculateur",
        "texte": "\n".join(lines),
    }
    return ToolOutput(content=response, passages=[calc_passage])


ASSET_CATEGORIES = list(wealth_tax.AssetCategory.__args__)

DEFAULT_TOOLS = [
    Tool(
        ToolSpec(
            name="rechercher_textes",
            description=(
                "Recherche des passages dans le corpus officiel de textes fiscaux tunisiens "
                "(lois de finances, codes). Renvoie des articles avec leur texte. Utilise des "
                "requêtes courtes en français juridique ; lance plusieurs recherches si la "
                "question couvre plusieurs sujets."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "requete": {"type": "string", "description": "Requête en français, ex. « impôt sur la fortune seuil »."},
                    "nombre": {"type": "integer", "minimum": 1, "maximum": 8, "description": "Nombre de passages (5 par défaut)."},
                },
                "required": ["requete"],
            },
        ),
        search_texts,
    ),
    Tool(
        ToolSpec(
            name="calculer_impot_fortune",
            description=(
                "Calcule l'impôt sur la fortune (Art. 88) à partir du patrimoine d'une personne, "
                "avec les taux officiels validés. À utiliser dès qu'un montant d'impôt sur la "
                "fortune est demandé : ne calcule jamais toi-même. N'invente aucune valeur absente "
                "de la question."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "resident_in_tunisia": {"type": "boolean", "description": "La personne est-elle résidente fiscale en Tunisie ?"},
                    "assets": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "value_tnd": {"type": "number", "minimum": 0, "description": "Valeur en dinars."},
                                "location": {"type": "string", "enum": ["tunisie", "etranger"]},
                                "category": {"type": "string", "enum": ASSET_CATEGORIES},
                            },
                            "required": ["value_tnd", "location", "category"],
                        },
                    },
                    "deductible_debts_tnd": {"type": "number", "minimum": 0, "description": "Dettes déductibles en dinars (0 si aucune)."},
                },
                "required": ["resident_in_tunisia", "assets"],
            },
        ),
        compute_wealth_tax,
    ),
    Tool(
        ToolSpec(
            name=ASK_USER_TOOL,
            description=(
                "Termine le travail et renvoie au comptable la liste des informations manquantes "
                "indispensables pour répondre (ex. résidence fiscale, valeur d'un bien). À utiliser "
                "plutôt que de supposer une valeur."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "questions": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                },
                "required": ["questions"],
            },
        ),
        # Jamais exécuté : la boucle intercepte cet outil pour s'arrêter et rendre la main.
        lambda args, question: ToolOutput({}),
    ),
]
