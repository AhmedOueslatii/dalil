"""Client Gemini partagé, avec un délai maximal par appel.

Sans timeout, un appel qui traîne côté Google bloque indéfiniment sans lever
d'erreur : c'est ce qui figeait l'évaluation. Avec un timeout, l'appel échoue
proprement et la requête utilisateur reçoit une erreur au lieu d'attendre.
"""
from functools import lru_cache

from google import genai
from google.genai import types

from app.settings import get_settings

TIMEOUT_MS = 30_000


@lru_cache
def get_client() -> genai.Client:
    return genai.Client(
        api_key=get_settings().GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=TIMEOUT_MS),
    )
