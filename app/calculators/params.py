from datetime import date
from decimal import Decimal

from app import db


def load_parameters(calculator: str, as_of: date) -> tuple[dict[str, Decimal], list[dict]]:
    """Retourne (valeurs par clé, sources citables) des paramètres validés en vigueur."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.key, t.value, t.article, d.titre, d.source
                FROM tax_parameters t
                JOIN documents d ON d.id = t.document_id
                WHERE t.calculator = %s
                  AND t.validated_at IS NOT NULL
                  AND t.valid_from <= %s
                  AND (t.valid_to IS NULL OR t.valid_to >= %s)
                """,
                (calculator, as_of, as_of),
            )
            rows = cur.fetchall()

    values = {row["key"]: row["value"] for row in rows}
    sources = []
    for row in rows:
        source = {"article": row["article"], "document": row["titre"], "source": row["source"]}
        if source not in sources:
            sources.append(source)
    return values, sources
