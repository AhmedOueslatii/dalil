-- Les lignes existantes sont des questions de test posées pendant le développement,
-- sans utilisateur réel associé : aucune valeur à conserver avant d'imposer NOT NULL.
DELETE FROM questions;

-- Isolation par utilisateur (authentification Supabase) : chaque question est
-- rattachée à l'utilisateur qui l'a posée. user_id est l'UUID Supabase (auth.users.id),
-- pas une clé étrangère SQL classique car auth.users vit dans le projet Supabase,
-- pas dans cette base PostgreSQL locale.
ALTER TABLE questions ADD COLUMN user_id UUID NOT NULL;

-- Index pour que "mes questions" (filtre par user_id) reste rapide même avec
-- beaucoup de questions accumulées tous utilisateurs confondus.
CREATE INDEX idx_questions_user_id ON questions (user_id);
