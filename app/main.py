"""Point d'entrée FastAPI."""
import tempfile
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import corpus, db
from app.auth import get_current_admin_id, get_current_user_id, is_admin
from app.calculators import wealth_tax
from app.calculators.params import load_parameters
from app.db import close_pool, open_pool, ping
from app.generate import generate_answer, log_question
from app.ingest import ingest_pdf

MAX_PDF_BYTES = 20 * 1024 * 1024


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
    id: int
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
    result["id"] = log_question(payload.question, result, user_id)
    return result


class FeedbackRequest(BaseModel):
    rating: Literal[-1, 1]
    wrong_citation: bool = False
    comment: str | None = Field(default=None, max_length=2000)


@app.post("/questions/{question_id}/feedback")
def give_feedback(question_id: int, payload: FeedbackRequest, user_id: str = Depends(get_current_user_id)):
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            # Même isolation que /questions : on ne peut noter que ses propres réponses.
            # 404 plutôt que 403 pour ne pas révéler l'existence d'une question d'autrui.
            cur.execute("SELECT 1 FROM questions WHERE id = %s AND user_id = %s", (question_id, user_id))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Question introuvable")

            cur.execute(
                """
                INSERT INTO answer_feedback (question_id, user_id, rating, wrong_citation, comment)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (question_id, user_id)
                DO UPDATE SET rating = EXCLUDED.rating, wrong_citation = EXCLUDED.wrong_citation,
                              comment = EXCLUDED.comment, created_at = now()
                """,
                (question_id, user_id, payload.rating, payload.wrong_citation, payload.comment),
            )
        conn.commit()
    return {"status": "ok"}


@app.get("/me")
def me(user_id: str = Depends(get_current_user_id)):
    # Sert au frontend à n'afficher le lien du tableau de bord qu'aux admins ; la
    # vraie protection reste get_current_admin_id côté /admin/dashboard.
    return {"is_admin": is_admin(user_id)}


@app.post("/calculs/impot-fortune")
def wealth_tax_calculation(
    payload: wealth_tax.WealthTaxInput, _user_id: str = Depends(get_current_user_id)
):
    # Aucun appel LLM ici : les données viennent du formulaire, les taux de
    # tax_parameters. Rien à anonymiser ni de tokens à journaliser.
    params, sources = load_parameters(wealth_tax.CALCULATOR, date.today())
    if any(key not in params for key in wealth_tax.REQUIRED_PARAMS):
        raise HTTPException(status_code=503, detail="Paramètres de calcul non disponibles pour cette date")

    result = wealth_tax.compute(payload, params)
    return wealth_tax.build_response(result, payload.resident_in_tunisia, sources)


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
                    count(*) FILTER (WHERE rating = 1) AS positive,
                    count(*) FILTER (WHERE rating = -1) AS negative,
                    count(*) FILTER (WHERE wrong_citation) AS wrong_citations
                FROM answer_feedback
                """
            )
            feedback = cur.fetchone()

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
        "feedback": feedback,
        "by_day": by_day,
        "note": "Estimation basée uniquement sur les tokens de génération ; les tokens d'embedding ne sont pas comptabilisés.",
    }


@app.get("/admin/documents")
def admin_list_documents(_admin_id: str = Depends(get_current_admin_id)):
    return {"documents": corpus.list_documents(), "indexing": corpus.indexing_status()}


@app.post("/admin/documents", status_code=201)
def admin_upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    titre: str = Form(..., min_length=3, max_length=300),
    date_texte: date | None = Form(None),
    _admin_id: str = Depends(get_current_admin_id),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
    source = Path(file.filename).name
    # Pas de dédoublonnage des chunks à la réingestion : on refuse plutôt un doublon
    # qui ferait apparaître chaque article deux fois dans les résultats de recherche.
    if corpus.source_exists(source):
        raise HTTPException(status_code=409, detail=f"Un document « {source} » existe déjà")

    content = file.file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF trop volumineux (20 Mo maximum)")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        document_id = ingest_pdf(tmp_path, titre, source, date_texte.isoformat() if date_texte else None)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=422, detail="PDF illisible")
    finally:
        tmp_path.unlink(missing_ok=True)

    # Les embeddings prennent plusieurs minutes : réponse immédiate, indexation en fond.
    background_tasks.add_task(corpus.run_indexing)
    return {"id": document_id}


@app.post("/admin/documents/reindex", status_code=202)
def admin_reindex(background_tasks: BackgroundTasks, _admin_id: str = Depends(get_current_admin_id)):
    background_tasks.add_task(corpus.run_indexing)
    return {"status": "started"}


@app.delete("/admin/documents/{document_id}", status_code=204)
def admin_delete_document(document_id: int, _admin_id: str = Depends(get_current_admin_id)):
    if not corpus.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document introuvable")
