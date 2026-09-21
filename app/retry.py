"""Retry avec backoff exponentiel pour les appels à l'API Gemini.

On a observé en pratique des 429 (quota dépassé) et 503 (modèle surchargé) qui sont
transitoires : la même requête repassée quelques secondes plus tard aboutit. On ne
retente PAS les autres codes (400, 401...) car ce sont des erreurs de requête ou
d'authentification qu'un retry ne résoudra jamais.
"""
import time

from google.genai import errors

RETRYABLE_CODES = {429, 503}
MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 2


def call_with_retry(func, *args, **kwargs):
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            return func(*args, **kwargs)
        except errors.APIError as e:
            if e.code not in RETRYABLE_CODES or attempt == MAX_ATTEMPTS - 1:
                raise
            last_error = e
            # Backoff exponentiel (2s, 4s, ...) : laisse le temps au quota/à la charge
            # de se résorber côté fournisseur plutôt que de marteler l'API en boucle.
            time.sleep(BASE_DELAY_SECONDS * (2 ** attempt))
    raise last_error
