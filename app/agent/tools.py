"""Outils de l'agent fiscal.

Chaque outil renvoie deux choses :
- `content` : ce que le LLM lit (dict JSON) ;
- `passages` : les éléments citables qui alimentent le garde-fou de sortie. Une phrase
  de la réponse finale ne survit que si l'article qu'elle cite et les chiffres qu'elle
  avance figurent dans ces passages (app/guardrails.py).

Un outil ne lève pas d'exception vers la boucle pour une erreur d'argument : il renvoie
{"erreur": ...} afin que le modèle corrige son appel au tour suivant.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from pydantic import ValidationError

from app.agent.llm import ToolSpec
from app.calculators import wealth_tax
from app.calculators.params import load_parameters
from app.search import hybrid_search

ASK_USER_TOOL = "demander_precisions"


@dataclass
class ToolOutput:
    content: dict
    passages: list[dict] = field(default_factory=list)


@dataclass
class Tool:
    spec: ToolSpec
    handler: Callable[[dict], ToolOutput]


def search_texts(args: dict) -> ToolOutput:
    query = str(args.get("requete", "")).strip()
    if not query:
        return ToolOutput({"erreur": "Le paramètre « requete » est vide."})
    top_k = max(1, min(int(args.get("nombre", 5)), 8))

    passages = hybrid_search(query, top_k=top_k)
    if not passages:
        return ToolOutput({"passages": [], "note": "Aucun passage trouvé. Reformule avec d'autres termes juridiques."})
    return ToolOutput(
        content={"passages": [{"article": p["article"], "document": p["titre"], "texte": p["texte"]} for p in passages]},
        passages=[{"article": p["article"], "titre": p["titre"], "source": p["source"], "texte": p["texte"]} for p in passages],
    )


def compute_wealth_tax(args: dict) -> ToolOutput:
    try:
        payload = wealth_tax.WealthTaxInput.model_validate(args)
    except ValidationError as exc:
        return ToolOutput({"erreur": f"Données invalides : {exc.errors(include_url=False)}"})

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
        lambda args: ToolOutput({}),
    ),
]
