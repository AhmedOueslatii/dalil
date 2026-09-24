"""Point d'entrée FastAPI."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import db
from app.auth import get_current_admin_id, get_current_user_id
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

# Le frontend tourne sur un serveur séparé (Vercel) : origine différente de l'API,
# donc CORS doit être autorisé explicitement sinon le navigateur bloque fetch().
# allow_origin_regex couvre le domaine stable (dalil-silk.vercel.app) et les URLs de
# déploiement générées à chaque push (dalil-<hash>-ahmedoueslatiis-projects.vercel.app),
# en plus du dev local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://dalil.*-ahmedoueslatiis-projects\.vercel\.app|https://dalil-silk\.vercel\.app",
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


# Pricing public gemini-flash-lite-latest (USD par million de tokens), à ajuster si
# Google change ses tarifs. Ne couvre QUE les tokens de génération : l'appel
# d'embedding fait dans hybrid_search() pour chaque question n'est pas loggé en base
# séparément, donc le coût réel total est légèrement sous-estimé ici.
PRICE_PER_MILLION_TOKENS_IN = 0.10
PRICE_PER_MILLION_TOKENS_OUT = 0.40


def estimate_cost_usd(tokens_in: int, tokens_out: int) -> float:
    return (
        tokens_in / 1_000_000 * PRICE_PER_MILLION_TOKENS_IN
        + tokens_out / 1_000_000 * PRICE_PER_MILLION_TOKENS_OUT
    )


@app.get("/admin/dashboard")
def admin_dashboard(_admin_id: str = Depends(get_current_admin_id)):
    # Vue globale tous utilisateurs confondus : réservée aux admins (get_current_admin_id
    # lève 403 sinon), contrairement à /questions qui reste isolé par utilisateur.
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    count(*) AS total_questions,
                    coalesce(sum(tokens_in), 0) AS total_tokens_in,
                    coalesce(sum(tokens_out), 0) AS total_tokens_out,
                    coalesce(avg(latence_ms), 0) AS avg_latence_ms
                FROM questions
                """
            )
            totals = cur.fetchone()

            cur.execute(
                """
                SELECT
                    date_trunc('day', created_at)::date AS day,
                    count(*) AS questions,
                    coalesce(sum(tokens_in), 0) AS tokens_in,
                    coalesce(sum(tokens_out), 0) AS tokens_out
                FROM questions
                WHERE created_at >= now() - interval '30 days'
                GROUP BY day
                ORDER BY day
                """
            )
            by_day = cur.fetchall()

    totals["estimated_cost_usd"] = round(
        estimate_cost_usd(totals["total_tokens_in"], totals["total_tokens_out"]), 4
    )
    for day in by_day:
        day["estimated_cost_usd"] = round(
            estimate_cost_usd(day["tokens_in"], day["tokens_out"]), 4
        )

    return {
        "totals": totals,
        "by_day": by_day,
        "note": "Estimation basée uniquement sur les tokens de génération ; les tokens d'embedding ne sont pas comptabilisés.",
    }
