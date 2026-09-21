"""Génération des embeddings des chunks (étape 3) via l'API Gemini.

Usage : python -m app.embed
Calcule l'embedding de tous les chunks dont embedding est encore NULL.
"""
import math

from google import genai
from google.genai import types

from app import db
from app.retry import call_with_retry
from app.settings import get_settings

EMBEDDING_MODEL = "gemini-embedding-001"

# Le modèle Gemini natif produit des vecteurs en 3072 dimensions ; on demande une
# sortie tronquée à EMBEDDING_DIM (768, imposé par la colonne `chunks.embedding vector(768)`
# créée à l'étape 1). Google documente que la troncature ne préserve PAS la norme
# unitaire du vecteur, donc on renormalise nous-mêmes pour que la similarité cosinus
# (utilisée par l'index HNSW `vector_cosine_ops`) reste comparable entre chunks.
def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector]


def embed_texts(client: genai.Client, texts: list[str], dim: int) -> list[list[float]]:
    result = call_with_retry(
        client.models.embed_content,
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=dim),
    )
    return [normalize(e.values) for e in result.embeddings]


def embed_missing_chunks(batch_size: int = 20) -> int:
    settings = get_settings()
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    total_embedded = 0
    with db.pool.connection() as conn:
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, texte FROM chunks WHERE embedding IS NULL ORDER BY id LIMIT %s",
                    (batch_size,),
                )
                rows = cur.fetchall()

            if not rows:
                break

            texts = [row["texte"] for row in rows]
            vectors = embed_texts(client, texts, settings.EMBEDDING_DIM)

            with conn.cursor() as cur:
                for row, vector in zip(rows, vectors):
                    cur.execute(
                        "UPDATE chunks SET embedding = %s WHERE id = %s",
                        (vector, row["id"]),
                    )
            conn.commit()

            total_embedded += len(rows)

    return total_embedded


def main():
    db.open_pool()
    try:
        count = embed_missing_chunks()
        print(f"{count} chunks embeddés.")
    finally:
        db.close_pool()


if __name__ == "__main__":
    main()
