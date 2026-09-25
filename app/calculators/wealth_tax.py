"""Impôt sur la fortune (Art. 88 de la LF 2026).

Module sans base de données ni LLM : le schéma du formulaire, le calcul et la mise
en forme. Les taux et seuils arrivent en paramètre (table tax_parameters), jamais
codés en dur ici.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, Field

CALCULATOR = "wealth_tax"
ARTICLE = "Art. 88"
REQUIRED_PARAMS = ("bracket_1_floor", "bracket_1_ceiling", "bracket_1_rate", "bracket_2_rate")

# Catégories calquées sur les exclusions de l'Art. 88 §3.
AssetCategory = Literal[
    "habitation_principale",
    "actif_professionnel",
    "vehicule_12cv_ou_moins",
    "vehicule_plus_de_12cv",
    "depot_bancaire_ou_postal",
    "autre",
]

EXCLUDED_CATEGORIES = {
    "habitation_principale": "habitation principale et meubles meublants",
    "actif_professionnel": "biens affectés à l'exploitation professionnelle",
    "vehicule_12cv_ou_moins": "véhicules non utilitaires de 12 CV ou moins",
    "depot_bancaire_ou_postal": "dépôts bancaires ou postaux",
}


class Asset(BaseModel):
    description: str = ""
    value_tnd: float = Field(ge=0)
    location: Literal["tunisie", "etranger"]
    category: AssetCategory


class WealthTaxInput(BaseModel):
    resident_in_tunisia: bool
    assets: list[Asset] = Field(min_length=1)
    deductible_debts_tnd: float = Field(default=0, ge=0)


def _d(value) -> Decimal:
    # str() avant Decimal : évite d'importer les erreurs d'arrondi binaire des float.
    return Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def compute(inputs: WealthTaxInput, params: dict[str, Decimal]) -> dict:
    floor = params["bracket_1_floor"]
    ceiling = params["bracket_1_ceiling"]
    rate_1 = params["bracket_1_rate"]
    rate_2 = params["bracket_2_rate"]

    taxable_assets = Decimal(0)
    excluded: dict[str, Decimal] = {}
    out_of_scope = Decimal(0)

    for asset in inputs.assets:
        value = _d(asset.value_tnd)
        # Un non-résident n'est imposable que sur ses biens situés en Tunisie (Art. 88 §2).
        if not inputs.resident_in_tunisia and asset.location != "tunisie":
            out_of_scope += value
        elif asset.category in EXCLUDED_CATEGORIES:
            label = EXCLUDED_CATEGORIES[asset.category]
            excluded[label] = excluded.get(label, Decimal(0)) + value
        else:
            taxable_assets += value

    debts = _d(inputs.deductible_debts_tnd)
    base = max(taxable_assets - debts, Decimal(0))

    # Lecture par tranches validée par l'administrateur : seule la part comprise entre
    # le plancher et le plafond supporte le premier taux, seule la part au-delà du
    # plafond supporte le second. Sous le plancher, aucun impôt.
    slice_1 = min(max(base - floor, Decimal(0)), ceiling - floor)
    slice_2 = max(base - ceiling, Decimal(0))
    tax_1 = _money(slice_1 * rate_1)
    tax_2 = _money(slice_2 * rate_2)

    return {
        "taxable_assets": _money(taxable_assets),
        "excluded": {label: _money(v) for label, v in excluded.items()},
        "out_of_scope": _money(out_of_scope),
        "debts": _money(debts),
        "base": _money(base),
        "slice_1": _money(slice_1),
        "slice_2": _money(slice_2),
        "tax_1": tax_1,
        "tax_2": tax_2,
        "total": tax_1 + tax_2,
        "floor": floor,
        "ceiling": ceiling,
        "rate_1": rate_1,
        "rate_2": rate_2,
    }


def fmt_tnd(value: Decimal) -> str:
    # Format français : espace pour les milliers, virgule et 3 décimales (millimes).
    integer, _, decimals = f"{value:.3f}".partition(".")
    grouped = f"{int(integer):,}".replace(",", " ")
    return f"{grouped},{decimals} TND"


def fmt_rate(rate: Decimal) -> str:
    return f"{(rate * 100).normalize():f}".replace(".", ",") + " %"


def build_response(result: dict, resident: bool, sources: list[dict]) -> dict:
    """Met en forme le résultat pour l'affichage : chaque ligne porte son article."""
    scope = "biens situés en Tunisie et à l'étranger" if resident else "biens situés en Tunisie uniquement"
    steps = [{"label": f"Biens imposables retenus ({scope})", "amount": fmt_tnd(result["taxable_assets"]), "article": ARTICLE}]
    for label, value in result["excluded"].items():
        steps.append({"label": f"Exclu : {label}", "amount": fmt_tnd(value), "article": ARTICLE})
    if result["out_of_scope"]:
        steps.append({"label": "Hors champ : biens hors de Tunisie d'un non-résident", "amount": fmt_tnd(result["out_of_scope"]), "article": ARTICLE})
    if result["debts"]:
        steps.append({"label": "Dettes déduites", "amount": fmt_tnd(result["debts"]), "article": ARTICLE})
    steps.append({"label": "Base imposable", "amount": fmt_tnd(result["base"]), "article": None})
    steps.append({
        "label": f"Part entre {fmt_tnd(result['floor'])} et {fmt_tnd(result['ceiling'])} "
                 f"({fmt_tnd(result['slice_1'])}) à {fmt_rate(result['rate_1'])}",
        "amount": fmt_tnd(result["tax_1"]),
        "article": ARTICLE,
    })
    steps.append({
        "label": f"Part au-delà de {fmt_tnd(result['ceiling'])} ({fmt_tnd(result['slice_2'])}) à {fmt_rate(result['rate_2'])}",
        "amount": fmt_tnd(result["tax_2"]),
        "article": ARTICLE,
    })

    return {
        "total": fmt_tnd(result["total"]),
        "steps": steps,
        "notes": [
            {"text": "Déclaration à déposer au plus tard à la fin du mois de juin.", "article": ARTICLE},
            {"text": "Estimation à vérifier par un professionnel avant toute déclaration.", "article": None},
        ],
        "sources": sources,
    }
