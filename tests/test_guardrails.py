from app.guardrails import DONT_KNOW, normalize_number, validate_answer

PASSAGES = [
    {
        "article": "Article premier",
        "texte": "Recettes du budget de l'Etat 52 560 000 000 Dinars. Dépenses 63 575 000 000 Dinars.",
    },
    {"article": "Art. 2", "texte": "Les recettes fiscales 47 773 000 000 Dinars pour l'année 2026."},
    {"article": "Art.  4", "texte": "Le montant des recettes des comptes de concours est fixé à 53 104 000 Dinars."},
    {"article": "Art. 88", "texte": "0,5% de la fortune dont la valeur varie de 3 millions de dinars à 5 millions."},
]
QUESTION = "Quel est le montant des recettes du budget de l'Etat pour 2026 ?"


def test_correct_answer_is_kept_untouched():
    answer = "Les recettes sont estimées à 52 560 000 000 Dinars [Article premier]."
    filtered, report = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == answer
    assert report["removed"] == []


def test_citation_outside_sources_is_removed():
    answer = (
        "Les recettes sont estimées à 52 560 000 000 Dinars [Article premier]. "
        "Le taux normal de TVA est de 19 % [Art. 18]."
    )
    filtered, report = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == "Les recettes sont estimées à 52 560 000 000 Dinars [Article premier]."
    assert report["removed"][0]["reason"] == "citation_hors_sources"


def test_invented_number_is_removed_even_with_valid_citation():
    answer = (
        "Les recettes sont estimées à 52 560 000 000 Dinars [Article premier]. "
        "Les recettes fiscales atteignent 50 000 000 000 Dinars [Art. 2]."
    )
    filtered, report = validate_answer(answer, PASSAGES, QUESTION)
    assert "50 000 000 000" not in filtered
    assert report["removed"][0]["reason"] == "chiffre_absent_des_sources"


def test_number_must_come_from_the_cited_article_not_any_passage():
    # 63 575 000 000 existe dans l'Article premier, pas dans l'Art. 2 cité ici.
    answer = "Les dépenses atteignent 63 575 000 000 Dinars [Art. 2]."
    filtered, report = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == DONT_KNOW
    assert report["fallback_dont_know"] is True


def test_uncited_number_is_removed():
    answer = "Les recettes sont de 52 560 000 000 Dinars [Article premier]. Cela représente 12 % de plus."
    filtered, report = validate_answer(answer, PASSAGES, QUESTION)
    assert "12 %" not in filtered
    assert report["removed"][0]["reason"] == "chiffre_non_cite"


def test_numbers_from_the_question_are_allowed():
    # « 2026 » vient de la question, pas forcément du passage de l'Article premier.
    answer = "Pour 2026, les recettes sont estimées à 52 560 000 000 Dinars [Article premier]."
    filtered, _ = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == answer


def test_uncited_sentence_repeating_question_number_is_kept():
    # Cas réel observé : phrase d'introduction qui reprend l'année de la question.
    answer = (
        "Pour l'année 2026, les recettes se répartissent comme suit :\n"
        "- Recettes fiscales : 47 773 000 000 Dinars [Art. 2]"
    )
    filtered, report = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == answer
    assert report["removed"] == []


def test_article_with_double_space_in_source_matches():
    answer = "Les comptes de concours s'élèvent à 53 104 000 Dinars [Art. 4]."
    filtered, _ = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == answer


def test_decimal_rate_formats_match():
    answer = "Le taux est de 0,5 % entre 3 et 5 millions de dinars [Art. 88]."
    filtered, _ = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == answer


def test_uncited_connecting_text_without_numbers_is_kept():
    answer = "Voici la réponse.\n- Recettes fiscales : 47 773 000 000 Dinars [Art. 2]"
    filtered, _ = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == answer


def test_nothing_sourced_left_becomes_dont_know():
    answer = "Le taux normal de TVA est de 19 % [Art. 18]."
    filtered, report = validate_answer(answer, PASSAGES, QUESTION)
    assert filtered == DONT_KNOW
    assert report["fallback_dont_know"] is True


def test_dont_know_passes_through():
    filtered, report = validate_answer("Je ne sais pas.", PASSAGES, QUESTION)
    assert filtered == DONT_KNOW
    assert report["removed"] == []


def test_normalize_number():
    assert normalize_number("52 560 000 000") == "52560000000"
    assert normalize_number("1.500.000") == "1500000"
    assert normalize_number("3,5") == "3.5"
    assert normalize_number("0,50") == "0.5"
    assert normalize_number("2026") == "2026"
