-- Système de rôles pour le dashboard de coût (vue admin globale).
-- user_id référence auth.users de Supabase (comme questions.user_id) : pas de clé
-- étrangère SQL classique, auth.users vit dans le schéma auth du même projet
-- Supabase mais on ne veut pas coupler notre schéma applicatif à son implémentation.
CREATE TABLE user_roles (
    user_id UUID PRIMARY KEY,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
