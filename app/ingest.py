"""Ingestion PDF : extraction du texte, découpage par article, insertion en base.

Usage : python -m app.ingest <chemin.pdf> --titre "..." --date 2025-12-12
"""
import argparse
import re
from pathlib import Path

import pymupdf

from app import db
from app.db import close_pool, open_pool

# Détecte "Article premier" ou "Art. <numéro>" suivi d'un tiret (simple, moyen ou cadratin).
# \s* autour du numéro car le PDF source contient parfois des doubles espaces ("Art.  4").
ARTICLE_PATTERN = re.compile(r"(Article premier|Art\.\s*\d+)\s*[-–—]", re.IGNORECASE)

# Au-delà de cette taille, un article est sous-découpé (voir MAX_CHUNK_CHARS).
# Choisi à partir de la distribution réelle observée sur Loi2025_17-1.pdf : la médiane
# des articles fait ~740 caractères, donc 1500 ne coupe que la queue longue (24/105 articles).
MAX_CHUNK_CHARS = 1500


def extract_text(pdf_path: Path) -> str:
    doc = pymupdf.open(pdf_path)
    return "\n".join(page.get_text() for page in doc)


def split_into_articles(full_text: str) -> list[tuple[str, str]]:
    """Découpe le texte en (numéro_article, texte_article) à partir des marqueurs Art./Article premier."""
    matches = list(ARTICLE_PATTERN.finditer(full_text))
    articles = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        numero = m.group(1).strip()
        texte = full_text[start:end].strip()
        articles.append((numero, texte))
    return articles


def split_long_chunk(texte: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Sous-découpe un article trop long, sur des frontières de paragraphe plutôt qu'au milieu d'une phrase."""
    if len(texte) <= max_chars:
        return [texte]

    paragraphs = texte.split("\n")
    parts = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 1 > max_chars:
            parts.append(current.strip())
            current = para
        else:
            current = f"{current}\n{para}" if current else para
    if current.strip():
        parts.append(current.strip())
    return parts


def ingest_pdf(pdf_path: Path, titre: str, source: str, date_texte: str | None, langue: str = "fr") -> int:
    full_text = extract_text(pdf_path)
    articles = split_into_articles(full_text)

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (titre, source, date_texte, langue) VALUES (%s, %s, %s, %s) RETURNING id",
                (titre, source, date_texte, langue),
            )
            document_id = cur.fetchone()["id"]

            ordre = 0
            for numero, texte_article in articles:
                # Un article trop long est sous-découpé, mais chaque morceau garde le même
                # numéro d'article : une citation pointera toujours vers l'article entier.
                for part in split_long_chunk(texte_article):
                    cur.execute(
                        """
                        INSERT INTO chunks (document_id, ordre, article, texte)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (document_id, ordre, numero, part),
                    )
                    ordre += 1

        conn.commit()

    return document_id


def main():
    parser = argparse.ArgumentParser(description="Ingestion d'un PDF de texte fiscal dans Dalil.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--titre", required=True)
    parser.add_argument("--source", default=None, help="Défaut : nom du fichier PDF.")
    parser.add_argument("--date", dest="date_texte", default=None, help="Format YYYY-MM-DD.")
    parser.add_argument("--langue", default="fr")
    args = parser.parse_args()

    source = args.source or args.pdf_path.name

    open_pool()
    try:
        document_id = ingest_pdf(args.pdf_path, args.titre, source, args.date_texte, args.langue)
        with db.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) AS count FROM chunks WHERE document_id = %s", (document_id,))
                count = cur.fetchone()["count"]
        print(f"Document {document_id} ingéré : {count} chunks créés.")
    finally:
        close_pool()


if __name__ == "__main__":
    main()
