from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.calculators.wealth_tax import Asset, WealthTaxInput, build_response, compute, fmt_tnd

PARAMS = {
    "bracket_1_floor": Decimal("3000000"),
    "bracket_1_ceiling": Decimal("5000000"),
    "bracket_1_rate": Decimal("0.005"),
    "bracket_2_rate": Decimal("0.01"),
}
SOURCES = [{"article": "Art. 88", "document": "LF 2026", "source": "Loi2025_17-1.pdf"}]


def asset(value, category="autre", location="tunisie"):
    return Asset(value_tnd=value, location=location, category=category)


def inputs(assets, resident=True, debts=0):
    return WealthTaxInput(resident_in_tunisia=resident, assets=assets, deductible_debts_tnd=debts)


def test_below_floor_is_untaxed():
    assert compute(inputs([asset(2_900_000)]), PARAMS)["total"] == Decimal("0.000")


def test_first_bracket_only():
    # 4 MTND : seul 1 MTND dépasse le plancher, à 0,5 %.
    assert compute(inputs([asset(4_000_000)]), PARAMS)["total"] == Decimal("5000.000")


def test_both_brackets_marginal():
    # 6 MTND : 2 MTND à 0,5 % + 1 MTND à 1 % = 20 000, pas 60 000 (taux global).
    result = compute(inputs([asset(6_000_000)]), PARAMS)
    assert result["tax_1"] == Decimal("10000.000")
    assert result["tax_2"] == Decimal("10000.000")
    assert result["total"] == Decimal("20000.000")


def test_exclusions_are_not_taxed():
    assets = [
        asset(6_000_000),
        asset(2_000_000, category="habitation_principale"),
        asset(500_000, category="depot_bancaire_ou_postal"),
        asset(150_000, category="vehicule_12cv_ou_moins"),
        asset(1_000_000, category="actif_professionnel"),
    ]
    result = compute(inputs(assets), PARAMS)
    assert result["taxable_assets"] == Decimal("6000000.000")
    assert result["total"] == Decimal("20000.000")


def test_vehicle_above_12cv_is_taxed():
    result = compute(inputs([asset(4_000_000), asset(200_000, category="vehicule_plus_de_12cv")]), PARAMS)
    assert result["taxable_assets"] == Decimal("4200000.000")


def test_non_resident_only_taxed_on_tunisian_assets():
    assets = [asset(4_000_000, location="tunisie"), asset(10_000_000, location="etranger")]
    result = compute(inputs(assets, resident=False), PARAMS)
    assert result["base"] == Decimal("4000000.000")
    assert result["out_of_scope"] == Decimal("10000000.000")


def test_resident_taxed_on_foreign_assets_too():
    assets = [asset(4_000_000, location="tunisie"), asset(2_000_000, location="etranger")]
    assert compute(inputs(assets), PARAMS)["base"] == Decimal("6000000.000")


def test_debts_reduce_base_but_never_below_zero():
    assert compute(inputs([asset(6_000_000)], debts=1_000_000), PARAMS)["total"] == Decimal("10000.000")
    assert compute(inputs([asset(1_000_000)], debts=5_000_000), PARAMS)["base"] == Decimal("0.000")


def test_form_requires_at_least_one_asset():
    with pytest.raises(ValidationError):
        inputs([])


def test_form_rejects_negative_values():
    with pytest.raises(ValidationError):
        inputs([asset(-1)])


def test_build_response_cites_every_computed_line():
    response = build_response(compute(inputs([asset(6_000_000)]), PARAMS), resident=True, sources=SOURCES)
    assert response["total"] == "20 000,000 TND"
    rate_lines = [s for s in response["steps"] if "à 0,5 %" in s["label"] or "à 1 %" in s["label"]]
    assert len(rate_lines) == 2
    assert all(s["article"] == "Art. 88" for s in rate_lines)
    assert response["sources"] == SOURCES


def test_fmt_tnd():
    assert fmt_tnd(Decimal("1234567.5")) == "1 234 567,500 TND"
