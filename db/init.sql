-- Extension pgvector pour stocker et indexer des vecteurs d'embeddings.
CREATE EXTENSION IF NOT EXISTS vector;
-- Extension unaccent pour que la recherche plein texte ignore les accents
-- (utile en français : "impôt" doit matcher "impot").
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Configuration de recherche plein texte française qui retire les accents avant
-- d'appliquer les règles linguistiques du français (racinisation, mots vides).
CREATE TEXT SEARCH CONFIGURATION fr_unaccent (COPY = french);
ALTER TEXT SEARCH CONFIGURATION fr_unaccent
    ALTER MAPPING FOR hword, hword_part, word WITH unaccent, french_stem;

-- Documents source (codes fiscaux, notes communes, circulaires...).
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    titre TEXT NOT NULL,
    source TEXT NOT NULL,
    date_texte DATE,
    langue TEXT NOT NULL DEFAULT 'fr'
);

-- Chunks : unités de texte découpées dans un document (typiquement un article),
-- avec leur embedding pour la recherche sémantique.
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordre INTEGER NOT NULL,
    article TEXT,
    texte TEXT NOT NULL,
    -- 768 = dimension par défaut ; doit correspondre au modèle d'embedding choisi
    -- plus tard (configurable via EMBEDDING_DIM dans app/settings.py).
    embedding vector(768),
    -- Colonne générée : recalculée automatiquement par PostgreSQL à chaque
    -- insertion/mise à jour de `texte`, donc toujours synchronisée.
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('fr_unaccent', texte)) STORED
);

-- Questions posées et réponses générées, avec traçabilité des sources citées
-- et des coûts (règle non négociable : coût en tokens journalisé).
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    texte TEXT NOT NULL,
    reponse TEXT,
    sources JSONB,
    tokens_in INTEGER,
    tokens_out INTEGER,
    latence_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index GIN pour accélérer la recherche plein texte sur tsv.
CREATE INDEX idx_chunks_tsv ON chunks USING GIN (tsv);

-- Index HNSW pour accélérer la recherche par similarité cosinus sur l'embedding
-- (nécessaire dès qu'on a beaucoup de chunks, sinon PostgreSQL scanne tout).
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);
