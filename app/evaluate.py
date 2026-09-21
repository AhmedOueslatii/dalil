"""Évaluation (étape 7) : mesure la qualité du pipeline sur le jeu de référence.

Usage : python -m app.evaluate

Mesure, pour chaque question du gold set :
- citations correctes : les articles cités dans la réponse correspondent-ils aux
  articles attendus (pour les questions dans le périmètre du corpus) ?
- "je ne sais pas" à bon escient : le système répond-il "Je ne sais pas." exactement
  quand il le faut (hors périmètre) et ne le fait-il PAS quand il ne le faut pas ?
- latence et coût en tokens, agrégés sur l'ensemble du jeu de référence.
"""
import re

from app import db
from app.generate import generate_answer

# Extrait les articles cités dans la réponse, au même format que le prompt système
# les impose ("[Art. X]" ou "[Article premier]").
CITATION_PATTERN = re.compile(r"\[(Article premier|Art\.\s*\d+)\]")


def extract_cited_articles(reponse: str) -> set[str]:
    return set(CITATION_PATTERN.findall(reponse))


def evaluate_case(case: dict) -> dict:
    print(f"... {case['question']}", flush=True)
    result = generate_answer(case["question"])
    expected = set(case["expected_articles"])
    cited = extract_cited_articles(result["reponse"])

    is_dont_know_expected = len(expected) == 0
    is_dont_know_actual = result["reponse"].strip().startswith("Je ne sais pas")

    return {
        "question": case["question"],
        "reponse": result["reponse"],
        "expected_articles": expected,
        "cited_articles": cited,
        # Pour une question dans le périmètre : au moins un article attendu est cité.
        # On ne demande pas une correspondance exacte, car le modèle peut légitimement
        # citer un article de soutien en plus de l'article principal attendu.
        "citation_correct": bool(expected & cited) if not is_dont_know_expected else None,
        "dont_know_expected": is_dont_know_expected,
        "dont_know_actual": is_dont_know_actual,
        "dont_know_correct": is_dont_know_expected == is_dont_know_actual,
        "tokens_in": result["tokens_in"],
        "tokens_out": result["tokens_out"],
        "latence_ms": result["latence_ms"],
    }


def run_evaluation(gold_set: list[dict]) -> dict:
    cases = [evaluate_case(case) for case in gold_set]

    in_scope_cases = [c for c in cases if not c["dont_know_expected"]]
    citation_accuracy = (
        sum(1 for c in in_scope_cases if c["citation_correct"]) / len(in_scope_cases)
        if in_scope_cases
        else None
    )
    dont_know_accuracy = sum(1 for c in cases if c["dont_know_correct"]) / len(cases)

    return {
        "cases": cases,
        "citation_accuracy": citation_accuracy,
        "dont_know_accuracy": dont_know_accuracy,
        "total_tokens_in": sum(c["tokens_in"] for c in cases),
        "total_tokens_out": sum(c["tokens_out"] for c in cases),
        "avg_latence_ms": sum(c["latence_ms"] for c in cases) / len(cases),
    }


def print_report(report: dict) -> None:
    for c in report["cases"]:
        status = "OK" if (c["citation_correct"] in (True, None)) and c["dont_know_correct"] else "FAIL"
        print(f"[{status}] {c['question']}")
        print(f"       attendu={c['expected_articles'] or '(je ne sais pas)'} cité={c['cited_articles']}")
        print(f"       latence={c['latence_ms']}ms tokens={c['tokens_in']}/{c['tokens_out']}")
        print()

    print("--- Résumé ---")
    if report["citation_accuracy"] is not None:
        print(f"Précision des citations : {report['citation_accuracy']:.0%}")
    print(f"Précision « je ne sais pas » : {report['dont_know_accuracy']:.0%}")
    print(f"Tokens totaux in/out : {report['total_tokens_in']}/{report['total_tokens_out']}")
    print(f"Latence moyenne : {report['avg_latence_ms']:.0f}ms")


def main():
    from tests.gold_set import GOLD_SET

    db.open_pool()
    try:
        report = run_evaluation(GOLD_SET)
        print_report(report)
    finally:
        db.close_pool()


if __name__ == "__main__":
    main()
