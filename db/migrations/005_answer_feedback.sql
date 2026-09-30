-- Retour des utilisateurs sur chaque réponse : utile / pas utile, et signalement
-- d'une citation erronée. Sert d'indicateur de qualité (tableau de bord) et de
-- réserve de vraies questions pour enrichir le jeu d'évaluation.
CREATE TABLE answer_feedback (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    wrong_citation BOOLEAN NOT NULL DEFAULT false,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Un seul avis par utilisateur et par réponse : un nouveau clic remplace l'ancien.
    UNIQUE (question_id, user_id)
);
