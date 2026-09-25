"""Génération citée (étape 5) : réponse à une question uniquement à partir des
passages trouvés par la recherche hybride, avec citations obligatoires.

Usage : python -m app.generate "quel est le montant des recettes du budget de l'Etat pour 2026 ?"
"""
import argparse
import time

from google import genai
from google.genai import types

from app import db
from app.anonymize import anonymize
from app.guardrails import validate_answer
from app.retry import call_with_retry
from app.search import hybrid_search
from app.settings import get_settings


# gemini-3.6-flash a un quota free tier de 20 requêtes/jour, épuisé pendant les tests.
# gemini-flash-lite-latest a un quota séparé, encore disponible au moment du choix.
GENERATION_MODEL = "gemini-flash-lite-latest"

# Prompt système qui porte la règle non négociable du CLAUDE.md : pas de réponse
# sans citation, "je ne sais pas" si les passages ne suffisent pas. On préfère
# instruire explicitement plutôt que de faire confiance au modèle par défaut,
# qui a tendance à compléter avec ses connaissances générales sinon.
SYSTEM_PROMPT = """Tu es un assistant fiscal pour des cabinets comptables tunisiens.

Règles strictes :
1. Réponds UNIQUEMENT à partir des passages fournis ci-dessous. N'utilise aucune
   connaissance extérieure, même si tu penses la connaître.
2. Chaque affirmation de ta réponse doit être suivie d'une citation entre crochets
   au format [Art. X] reprenant exactement le numéro d'article du passage utilisé.
3. Si les passages fournis ne permettent pas de répondre à la question, réponds
   exactement : "Je ne sais pas." N'invente jamais de réponse partielle.
4. Reprends les montants, taux et dates exactement comme ils sont écrits dans les
   passages, sans les arrondir ni les reformuler.
5. Réponds en français, de façon concise et professionnelle."""


def build_user_prompt(question: str, passages: list[dict]) -> str:
    passages_text = "\n\n".join(
        f"[{p['article']}] (source : {p['titre']})\n{p['texte']}" for p in passages
    )
    return f"Passages disponibles :\n\n{passages_text}\n\nQuestion : {question}"


def generate_answer(question: str, top_k: int = 5) -> dict:
    # Anonymisation avant tout appel LLM (règle non négociable du CLAUDE.md) : la
    # recherche hybride elle-même appelle Gemini pour embedder la question, donc le
    # masquage doit avoir lieu avant hybrid_search, pas seulement avant la génération.
    anonymized_question, client_mapping = anonymize(question)

    passages = hybrid_search(anonymized_question, top_k=top_k)

    # Rien trouvé par la recherche hybride : pas la peine d'appeler le LLM, la règle
    # "je ne sais pas" s'applique déjà avant tout appel (évite aussi un coût inutile).
    if not passages:
        return {
            "reponse": "Je ne sais pas.",
            "sources": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "latence_ms": 0,
        }

    settings = get_settings()
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    user_prompt = build_user_prompt(anonymized_question, passages)

    start = time.monotonic()
    response = call_with_retry(
        client.models.generate_content,
        model=GENERATION_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,  # déterministe : on veut la réponse la plus fidèle aux passages, pas de créativité
        ),
    )
    latence_ms = int((time.monotonic() - start) * 1000)

    # Vérification avant démasquage : les passages et la question sont comparés dans
    # leur forme anonymisée, celle que le LLM a réellement vue.
    reponse, guardrail = validate_answer(response.text, passages, anonymized_question)

    # Démasquage : le comptable doit voir le vrai nom de son client dans la réponse.
    # La confidentialité s'applique au LLM externe, pas au cabinet lui-même.
    for pseudo, original in client_mapping.items():
        reponse = reponse.replace(pseudo, original)

    sources = [
        {"article": p["article"], "document": p["titre"], "source": p["source"]}
        for p in passages
    ]

    return {
        "reponse": reponse,
        "sources": sources,
        "tokens_in": response.usage_metadata.prompt_token_count,
        "tokens_out": response.usage_metadata.candidates_token_count,
        "latence_ms": latence_ms,
        "guardrail": guardrail,
    }


def log_question(question: str, result: dict, user_id: str) -> None:
    import json

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO questions (texte, reponse, sources, tokens_in, tokens_out, latence_ms, user_id, guardrail)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    question,
                    result["reponse"],
                    json.dumps(result["sources"]),
                    result["tokens_in"],
                    result["tokens_out"],
                    result["latence_ms"],
                    user_id,
                    json.dumps(result["guardrail"]) if "guardrail" in result else None,
                ),
            )
        conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Génération citée pour une question fiscale.")
    parser.add_argument("question")
    args = parser.parse_args()

    db.open_pool()
    try:
        # Pas de log_question ici : l'usage CLI n'a pas d'utilisateur authentifié
        # (user_id est NOT NULL en base depuis l'ajout de l'isolation multi-utilisateurs).
        result = generate_answer(args.question)

        print(result["reponse"])
        print()
        print(f"Sources : {result['sources']}")
        print(f"Tokens in/out : {result['tokens_in']}/{result['tokens_out']}, latence : {result['latence_ms']}ms")
    finally:
        db.close_pool()


if __name__ == "__main__":
    main()
