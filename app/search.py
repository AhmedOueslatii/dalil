"""Recherche hybride (étape 4) : fusion de la recherche plein texte et vectorielle.

Usage : python -m app.search "quel est le montant des recettes du budget de l'Etat pour 2026 ?"
"""
import argparse

from google import genai
from google.genai import types
from pgvector import Vector

from app import db
from app.embed import EMBEDDING_MODEL, normalize
from app.retry import call_with_retry
from app.settings import get_settings

# Les scores ts_rank (plein texte) et distance cosinus (vectoriel) ne vivent pas sur
# la même échelle : on ne peut pas juste les additionner. RRF (Reciprocal Rank Fusion)
# évite ce problème en ne combinant que les RANGS de chaque méthode, pas les scores
# bruts. C'est la technique standard pour fusionner deux moteurs de recherche hétérogènes.
RRF_K = 60  # constante standard de la littérature RRF, amortit le poids des tout premiers rangs


def embed_query(query: str) -> list[float]:
    settings = get_settings()
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    result = call_with_retry(
        client.models.embed_content,
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(output_dimensionality=settings.EMBEDDING_DIM),
    )
    return normalize(result.embeddings[0].values)


def hybrid_search(query: str, top_k: int = 5, candidates: int = 20) -> list[dict]:
    """Retourne les top_k chunks les plus pertinents, fusion RRF plein texte + vectoriel."""
    query_vector = Vector(embed_query(query))

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            # Recherche plein texte : websearch_to_tsquery gère nativement les requêtes
            # en langage naturel (contrairement à plainto_tsquery qui perd les négations/phrases).
            cur.execute(
                """
                SELECT id, ts_rank(tsv, query) AS score
                FROM chunks, websearch_to_tsquery('fr_unaccent', %s) query
                WHERE tsv @@ query
                ORDER BY score DESC
                LIMIT %s
                """,
                (query, candidates),
            )
            fts_rows = cur.fetchall()

            # Recherche vectorielle : <=> est la distance cosinus (plus petit = plus proche).
            cur.execute(
                """
                SELECT id, embedding <=> %s AS distance
                FROM chunks
                WHERE embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT %s
                """,
                (query_vector, candidates),
            )
            vector_rows = cur.fetchall()

            fts_ranks = {row["id"]: rank for rank, row in enumerate(fts_rows, start=1)}
            vector_ranks = {row["id"]: rank for rank, row in enumerate(vector_rows, start=1)}

            rrf_scores: dict[int, float] = {}
            for chunk_id in set(fts_ranks) | set(vector_ranks):
                score = 0.0
                if chunk_id in fts_ranks:
                    score += 1 / (RRF_K + fts_ranks[chunk_id])
                if chunk_id in vector_ranks:
                    score += 1 / (RRF_K + vector_ranks[chunk_id])
                rrf_scores[chunk_id] = score

            top_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]
            if not top_ids:
                return []

            cur.execute(
                """
                SELECT c.id, c.article, c.texte, d.titre, d.source
                FROM chunks c JOIN documents d ON d.id = c.document_id
                WHERE c.id = ANY(%s)
                """,
                (top_ids,),
            )
            details = {row["id"]: row for row in cur.fetchall()}

    return [
        {**details[cid], "score_rrf": rrf_scores[cid]}
        for cid in top_ids
        if cid in details
    ]


def main():
    parser = argparse.ArgumentParser(description="Recherche hybride dans le corpus Dalil.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    db.open_pool()
    try:
        results = hybrid_search(args.query, top_k=args.top_k)
        for r in results:
            print(f"--- {r['article']} ({r['source']}) score={r['score_rrf']:.4f} ---")
            print(r["texte"][:200])
            print()
    finally:
        db.close_pool()


if __name__ == "__main__":
    main()
