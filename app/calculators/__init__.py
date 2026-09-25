"""Calculateurs cités : le LLM extrait les données, le code calcule.

Le LLM ne produit jamais de chiffre fiscal : il remplit un schéma strict à partir de
la question, puis une fonction déterministe calcule avec des paramètres validés
(table tax_parameters) qui portent chacun leur article source.
"""
import re
import time
from datetime import date

from google import genai
from google.genai import types

from app.calculators import wealth_tax
from app.calculators.params import load_parameters
from app.retry import call_with_retry
from app.settings import get_settings

# Filtre par mots-clés avant tout appel LLM : sans lui, chaque question du chat
# coûterait un appel d'extraction en plus, ce qui doublerait la consommation d'un
# quota Gemini gratuit déjà serré. L'extraction décide ensuite si c'est bien une
# demande de calcul ou une simple question d'information.
WEALTH_TAX_GATE = re.compile(r"\bfortune\b", re.IGNORECASE)

EXTRACTION_PROMPT = """Tu extrais des données pour un calcul d'impôt sur la fortune tunisien.
Ne calcule rien. Remplis uniquement le schéma à partir de la question.

- is_calculation_request : true seulement si l'utilisateur veut obtenir un montant
  d'impôt pour une situation donnée ; false pour une question d'information générale.
- resident_in_tunisia : null si la question ne le dit pas. Ne le suppose jamais.
- assets : un élément par bien mentionné, valeur en dinars (TND).
  location : "inconnue" si la question ne précise pas le pays.
  category :
    habitation_principale = résidence principale et ses meubles meublants ;
    actif_professionnel = immeubles, meubles ou fonds de commerce exploités pour
      l'activité professionnelle ;
    vehicule_12cv_ou_moins / vehicule_plus_de_12cv = véhicule non utilitaire selon
      sa puissance fiscale ; vehicule_puissance_inconnue si elle n'est pas donnée ;
    depot_bancaire_ou_postal = sommes déposées en banque ou à la Poste ;
    autre = tout autre bien.
- deductible_debts_tnd : null si aucune dette n'est mentionnée."""


def _no_answer(start: float, tokens_in: int = 0, tokens_out: int = 0) -> dict:
    return {
        "reponse": "Je ne sais pas.",
        "sources": [],
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latence_ms": int((time.monotonic() - start) * 1000),
    }


def try_calculation(question: str, model: str) -> dict | None:
    """Traite la question comme un calcul si c'en est un, sinon renvoie None.

    La question doit déjà être anonymisée : elle part vers le LLM d'extraction.
    """
    if not WEALTH_TAX_GATE.search(question):
        return None

    start = time.monotonic()
    client = genai.Client(api_key=get_settings().GEMINI_API_KEY)
    response = call_with_retry(
        client.models.generate_content,
        model=model,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=EXTRACTION_PROMPT,
            temperature=0,
            response_mime_type="application/json",
            response_schema=wealth_tax.WealthTaxExtraction,
        ),
    )
    tokens_in = response.usage_metadata.prompt_token_count
    tokens_out = response.usage_metadata.candidates_token_count
    extraction = response.parsed

    # Extraction illisible ou question d'information : la recherche documentaire
    # classique répondra mieux qu'un calcul.
    if extraction is None or not extraction.is_calculation_request:
        return None

    params, sources = load_parameters(wealth_tax.CALCULATOR, date.today())
    if any(key not in params for key in wealth_tax.REQUIRED_PARAMS):
        return _no_answer(start, tokens_in, tokens_out)

    missing = wealth_tax.missing_fields(extraction)
    if missing:
        reponse = (
            f"Pour calculer l'impôt sur la fortune [{wealth_tax.ARTICLE}], il me manque :\n"
            + "\n".join(f"- {item}" for item in missing)
            + "\n\nReposez votre question en précisant ces éléments."
        )
    else:
        result = wealth_tax.compute(extraction, params)
        reponse = wealth_tax.render(result, extraction.resident_in_tunisia)

    return {
        "reponse": reponse,
        "sources": sources,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latence_ms": int((time.monotonic() - start) * 1000),
    }
