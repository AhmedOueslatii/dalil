"""Configuration de l'application, lue depuis les variables d'environnement (.env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # pydantic-settings valide les types et centralise la config : ça évite les
    # `os.getenv` éparpillés dans le code et les erreurs silencieuses de typo.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    EMBEDDING_DIM: int = 768
    APP_ENV: str = "dev"
    GEMINI_API_KEY: str
    MISTRAL_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str


@lru_cache
def get_settings() -> Settings:
    # lru_cache : on ne relit le fichier .env qu'une seule fois par process,
    # les appels suivants réutilisent le même objet Settings.
    return Settings()
