"""Gestion du corpus depuis le tableau de bord admin : liste, ajout, indexation, suppression.

L'indexation (embeddings) prend plusieurs minutes et peut buter sur le quota Gemini.
Elle tourne donc en tâche de fond. Comme embed_missing_chunks ne traite que les
chunks sans embedding, une indexation interrompue se relance sans rien refaire.

L'état de l'indexation vit en mémoire du processus : suffisant tant que l'API tourne
avec un seul worker (cas actuel sur Render), à revoir si on passe à plusieurs.
"""
import logging
import threading

from app import db
from app.embed import embed_missing_chunks

logger = logging.getLogger(__name__)

_indexing_lock = threading.Lock()
_indexing_state = {"running": False, "last_error": None}


def list_documents() -> list[dict]:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id, d.titre, d.source, d.date_texte,
                       count(c.id) AS chunks,
                       count(c.embedding) AS embedded
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                GROUP BY d.id
                ORDER BY d.id
                """
            )
            return cur.fetchall()


def source_exists(source: str) -> bool:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM documents WHERE source = %s", (source,))
            return cur.fetchone() is not None


def delete_document(document_id: int) -> bool:
    # Les chunks sont supprimés en cascade (FK ON DELETE CASCADE dans init.sql).
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


def indexing_status() -> dict:
    return dict(_indexing_state)


def run_indexing() -> None:
    """Indexe les chunks sans embedding. Sans effet si une indexation tourne déjà."""
    # acquire non bloquant : deux indexations simultanées traiteraient les mêmes
    # chunks en double et consommeraient deux fois le quota.
    if not _indexing_lock.acquire(blocking=False):
        return
    _indexing_state.update(running=True, last_error=None)
    try:
        count = embed_missing_chunks()
        logger.info("Indexation terminée : %s chunks", count)
    except Exception as exc:
        logger.exception("Indexation interrompue")
        _indexing_state["last_error"] = str(exc)[:300]
    finally:
        _indexing_state["running"] = False
        _indexing_lock.release()
