-- Rapport du garde-fou de sortie (app/guardrails.py) pour chaque question : phrases
-- retirées et raison, repli sur « Je ne sais pas ». Permet de mesurer à quelle
-- fréquence le LLM cite hors sources ou invente un chiffre. NULL quand aucun appel
-- LLM n'a eu lieu (aucun passage trouvé).
ALTER TABLE questions ADD COLUMN guardrail JSONB;
