"""Authentification (multi-utilisateurs) : vérifie le token Supabase de chaque requête.

Le frontend Next.js envoie le token JWT émis par Supabase Auth dans le header
Authorization. On le valide en interrogeant directement l'API Supabase (GET
/auth/v1/user) plutôt qu'en vérifiant la signature localement : plus simple à
configurer (pas de JWT secret à gérer côté backend), au prix d'un appel réseau
supplémentaire par requête.
"""
import httpx
from fastapi import Header, HTTPException

from app.settings import get_settings


async def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant ou mal formé")

    token = authorization.removeprefix("Bearer ")
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.SUPABASE_ANON_KEY,
            },
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    return response.json()["id"]
