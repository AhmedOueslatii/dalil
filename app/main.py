"""Point d'entrée FastAPI."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import db
from app.auth import get_current_user_id
from app.db import close_pool, open_pool, ping
from app.generate import generate_answer, log_question


@asynccontextmanager
async def lifespan(app: FastAPI):
    # lifespan garantit que le pool est ouvert avant la première requête et
    # fermé proprement à l'arrêt du serveur (pas de connexions qui traînent).
    open_pool()
    yield
    close_pool()


app = FastAPI(title="Dalil", lifespan=lifespan)

# Le frontend tourne sur un serveur séparé (fichier statique ouvert directement ou
# petit serveur de dev) : origine différente de l'API, donc CORS doit être autorisé
# explicitement sinon le navigateur bloque les requêtes fetch().
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # étape locale/dev uniquement ; à restreindre en production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return ping()


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    reponse: str
    sources: list[dict]
    tokens_in: int
    tokens_out: int
    latence_ms: int


@app.post("/questions", response_model=QuestionResponse)
def ask_question(payload: QuestionRequest, user_id: str = Depends(get_current_user_id)):
    # Route définie en `def` (pas `async def`) : generate_answer fait des appels
    # réseau bloquants (recherche + LLM). FastAPI exécute automatiquement les routes
    # synchrones dans un threadpool, donc ça ne bloque pas l'event loop principal.
    result = generate_answer(payload.question)
    log_question(payload.question, result, user_id)
    return result


@app.get("/questions")
def list_questions(limit: int = 20, user_id: str = Depends(get_current_user_id)):
    # Isolation stricte : chaque utilisateur ne voit que ses propres questions.
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, texte, reponse, sources, tokens_in, tokens_out, latence_ms, created_at
                FROM questions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return cur.fetchall()
