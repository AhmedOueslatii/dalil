"""Journalisation des exécutions de l'agent (table agent_runs, migration 006)."""
import json

from app import db


def log_agent_run(question: str, result: dict, user_id: str) -> int:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_runs (user_id, question, reponse, statut, sources, trace, guardrail,
                                        appels_llm, tokens_in, tokens_out, latence_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    question,
                    result["reponse"],
                    result["statut"],
                    json.dumps(result["sources"]),
                    json.dumps(result["trace"]),
                    json.dumps(result["guardrail"]) if result["guardrail"] is not None else None,
                    result["appels_llm"],
                    result["tokens_in"],
                    result["tokens_out"],
                    result["latence_ms"],
                ),
            )
            run_id = cur.fetchone()["id"]
        conn.commit()
    return run_id
