"""Impôt sur la fortune (Art. 88 de la LF 2026).

Module sans base de données ni LLM : le schéma d'extraction, la détection des
informations manquantes, le calcul et la mise en forme. Les taux et seuils arrivent
en paramètre (table tax_parameters), jamais codés en dur ici.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel

CALCULATOR = "wealth_tax"
ARTICLE = "Art. 88"
REQUIRED_PARAMS = ("bracket_1_floor", "bracket_1_ceiling", "bracket_1_rate", "bracket_2_rate")

# Catégories calquées sur les exclusions de l'Art. 88 §3. Les valeurs "inconnue"
# existent pour que le LLM n'ait jamais à deviner : une catégorie ou une localisation
# inconnue qui change le résultat devient une question posée à l'utilisateur.
AssetCategory = Literal[
    "habitation_principale",
    "actif_professionnel",
    "vehicule_12cv_ou_moins",
    "vehicule_plus_de_12cv",
    "vehicule_puissance_inconnue",
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
    description: str
    value_tnd: float
    location: Literal["tunisie", "etranger", "inconnue"]
    category: AssetCategory


class WealthTaxExtraction(BaseModel):
    is_calculation_request: bool
    resident_in_tunisia: bool | None
    assets: list[Asset]
    deductible_debts_tnd: float | None


def missing_fields(extraction: WealthTaxExtraction) -> list[str]:
    missing = []
    if extraction.resident_in_tunisia is None:
        missing.append("la résidence fiscale (résident en Tunisie ou non)")
    if not extraction.assets:
        missing.append("la liste des biens avec leur valeur en dinars")
    for asset in extraction.assets:
        if asset.category == "vehicule_puissance_inconnue":
            missing.append(f"la puissance fiscale du véhicule « {asset.description} »")
        # La localisation ne compte que pour un non-résident, seuls ses biens en
        # Tunisie étant imposables (Art. 88 §2).
        if extraction.resident_in_tunisia is False and asset.location == "inconnue":
            missing.append(f"la localisation (Tunisie ou étranger) de « {asset.description} »")
    return missing


def _d(value) -> Decimal:
    # str() avant Decimal : évite d'importer les erreurs d'arrondi binaire des float.
    return Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def compute(extraction: WealthTaxExtraction, params: dict[str, Decimal]) -> dict:
    floor = params["bracket_1_floor"]
    ceiling = params["bracket_1_ceiling"]
    rate_1 = params["bracket_1_rate"]
    rate_2 = params["bracket_2_rate"]

    taxable_assets = Decimal(0)
    excluded: dict[str, Decimal] = {}
    out_of_scope = Decimal(0)

    for asset in extraction.assets:
        value = _d(asset.value_tnd)
        if not extraction.resident_in_tunisia and asset.location != "tunisie":
            out_of_scope += value
        elif asset.category in EXCLUDED_CATEGORIES:
            label = EXCLUDED_CATEGORIES[asset.category]
            excluded[label] = excluded.get(label, Decimal(0)) + value
        else:
            taxable_assets += value

    debts = _d(extraction.deductible_debts_tnd or 0)
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
        "debts_mentioned": extraction.deductible_debts_tnd is not None,
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


def render(result: dict, resident: bool) -> str:
    cite = f"[{ARTICLE}]"
    lines = [f"Impôt sur la fortune estimé : {fmt_tnd(result['total'])} {cite}", "", "Détail du calcul :"]

    scope = "biens situés en Tunisie et à l'étranger" if resident else "biens situés en Tunisie uniquement"
    lines.append(f"- Biens imposables retenus ({scope}) : {fmt_tnd(result['taxable_assets'])} {cite}")
    for label, value in result["excluded"].items():
        lines.append(f"- Exclu ({label}) : {fmt_tnd(value)} {cite}")
    if result["out_of_scope"]:
        lines.append(f"- Hors champ (biens hors de Tunisie d'un non-résident) : {fmt_tnd(result['out_of_scope'])} {cite}")

    if result["debts_mentioned"]:
        lines.append(f"- Dettes déduites : {fmt_tnd(result['debts'])} {cite}")
    lines.append(f"- Base imposable : {fmt_tnd(result['base'])}")

    lines.append(
        f"- Part entre {fmt_tnd(result['floor'])} et {fmt_tnd(result['ceiling'])} "
        f"({fmt_tnd(result['slice_1'])}) à {fmt_rate(result['rate_1'])} : {fmt_tnd(result['tax_1'])} {cite}"
    )
    lines.append(
        f"- Part au-delà de {fmt_tnd(result['ceiling'])} "
        f"({fmt_tnd(result['slice_2'])}) à {fmt_rate(result['rate_2'])} : {fmt_tnd(result['tax_2'])} {cite}"
    )

    lines += ["", f"Déclaration à déposer au plus tard à la fin du mois de juin {cite}."]
    if not result["debts_mentioned"]:
        lines.append("Hypothèse : aucune dette déduite, faute d'information dans la question.")
    lines.append("Estimation à vérifier par un professionnel avant toute déclaration.")
    return "\n".join(lines)
