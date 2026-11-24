-- Exécutions de l'agent fiscal (app/agent) : une ligne par question, avec la trace
-- complète (chaque appel LLM et chaque outil, arguments anonymisés, tokens, latence).
-- La trace sert à déboguer un agent qui tourne en rond et à mesurer son coût réel
-- (règle non négociable n° 3 : coût en tokens journalisé).
CREATE TABLE agent_runs (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    question TEXT NOT NULL,
    reponse TEXT NOT NULL,
    -- reponse | precisions_requises | budget_epuise
    statut TEXT NOT NULL,
    sources JSONB NOT NULL DEFAULT '[]',
    trace JSONB NOT NULL DEFAULT '[]',
    guardrail JSONB,
    appels_llm INTEGER NOT NULL,
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    latence_ms INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_runs_user_id ON agent_runs (user_id);
