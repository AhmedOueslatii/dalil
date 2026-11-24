"""Usage : python -m app.agent "Mon client résident a 6 MTND d'immeubles locatifs, combien d'impôt sur la fortune ?" [--trace]"""
import argparse
import json
import sys

from app import db
from app.agent.loop import run_agent


def main():
    parser = argparse.ArgumentParser(description="Agent fiscal Dalil.")
    parser.add_argument("question")
    parser.add_argument("--trace", action="store_true", help="Affiche chaque étape (appels LLM et outils).")
    args = parser.parse_args()
    # La console Windows n'est pas en UTF-8 par défaut : sans ça, les accents s'affichent en « � ».
    sys.stdout.reconfigure(encoding="utf-8")

    db.open_pool()
    try:
        result = run_agent(args.question)
    finally:
        db.close_pool()

    if args.trace:
        for step in result["trace"]:
            print(json.dumps(step, ensure_ascii=False, default=str))
        print()
    print(result["reponse"])
    print()
    print(f"Statut : {result['statut']} · appels LLM : {result['appels_llm']} · "
          f"tokens in/out : {result['tokens_in']}/{result['tokens_out']} · latence : {result['latence_ms']} ms")
    for s in result["sources"]:
        print(f"  - {s['article']} ({s['document']})")
    if result["guardrail"] and result["guardrail"]["removed"]:
        print(f"Garde-fou : {len(result['guardrail']['removed'])} phrase(s) retirée(s)")
        for removed in result["guardrail"]["removed"]:
            print(f"  - [{removed['reason']} {removed['detail']}] {removed['sentence']}")


if __name__ == "__main__":
    main()
