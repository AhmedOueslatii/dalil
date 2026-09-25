from decimal import Decimal

from app.calculators.wealth_tax import (
    Asset,
    WealthTaxExtraction,
    compute,
    fmt_tnd,
    missing_fields,
    render,
)

PARAMS = {
    "bracket_1_floor": Decimal("3000000"),
    "bracket_1_ceiling": Decimal("5000000"),
    "bracket_1_rate": Decimal("0.005"),
    "bracket_2_rate": Decimal("0.01"),
}


def asset(value, category="autre", location="tunisie", description="bien"):
    return Asset(description=description, value_tnd=value, location=location, category=category)


def extraction(assets, resident=True, debts=None):
    return WealthTaxExtraction(
        is_calculation_request=True,
        resident_in_tunisia=resident,
        assets=assets,
        deductible_debts_tnd=debts,
    )


def test_below_floor_is_untaxed():
    assert compute(extraction([asset(2_900_000)]), PARAMS)["total"] == Decimal("0.000")


def test_first_bracket_only():
    # 4 MTND : seul 1 MTND dépasse le plancher, à 0,5 %.
    assert compute(extraction([asset(4_000_000)]), PARAMS)["total"] == Decimal("5000.000")


def test_both_brackets_marginal():
    # 6 MTND : 2 MTND à 0,5 % + 1 MTND à 1 % = 20 000, pas 60 000 (taux global).
    result = compute(extraction([asset(6_000_000)]), PARAMS)
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
    result = compute(extraction(assets), PARAMS)
    assert result["taxable_assets"] == Decimal("6000000.000")
    assert result["total"] == Decimal("20000.000")


def test_vehicle_above_12cv_is_taxed():
    result = compute(extraction([asset(4_000_000), asset(200_000, category="vehicule_plus_de_12cv")]), PARAMS)
    assert result["taxable_assets"] == Decimal("4200000.000")


def test_non_resident_only_taxed_on_tunisian_assets():
    assets = [asset(4_000_000, location="tunisie"), asset(10_000_000, location="etranger")]
    result = compute(extraction(assets, resident=False), PARAMS)
    assert result["base"] == Decimal("4000000.000")
    assert result["out_of_scope"] == Decimal("10000000.000")


def test_resident_taxed_on_foreign_assets_too():
    assets = [asset(4_000_000, location="tunisie"), asset(2_000_000, location="etranger")]
    assert compute(extraction(assets), PARAMS)["base"] == Decimal("6000000.000")


def test_debts_reduce_base_but_never_below_zero():
    assert compute(extraction([asset(6_000_000)], debts=1_000_000), PARAMS)["total"] == Decimal("10000.000")
    assert compute(extraction([asset(1_000_000)], debts=5_000_000), PARAMS)["base"] == Decimal("0.000")


def test_missing_residency_and_assets():
    missing = missing_fields(extraction([], resident=None))
    assert len(missing) == 2


def test_missing_vehicle_power():
    missing = missing_fields(extraction([asset(100_000, category="vehicule_puissance_inconnue", description="4x4")]))
    assert missing == ["la puissance fiscale du véhicule « 4x4 »"]


def test_unknown_location_only_matters_for_non_residents():
    assert missing_fields(extraction([asset(4_000_000, location="inconnue")], resident=True)) == []
    assert len(missing_fields(extraction([asset(4_000_000, location="inconnue")], resident=False))) == 1


def test_render_cites_article_and_formats_amounts():
    text = render(compute(extraction([asset(6_000_000)]), PARAMS), resident=True)
    assert text.startswith("Impôt sur la fortune estimé : 20 000,000 TND [Art. 88]")
    assert "0,5 %" in text and "1 %" in text
    assert "aucune dette déduite" in text


def test_fmt_tnd():
    assert fmt_tnd(Decimal("1234567.5")) == "1 234 567,500 TND"
