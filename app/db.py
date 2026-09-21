"""Pool de connexions PostgreSQL (psycopg 3)."""
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.settings import get_settings

# Un pool plutôt qu'une connexion unique : FastAPI traite des requêtes concurrentes,
# et ouvrir une connexion PostgreSQL par requête serait trop lent.
pool: ConnectionPool | None = None


def open_pool() -> None:
    global pool
    settings = get_settings()
    # row_factory=dict_row : les lignes reviennent en dict plutôt qu'en tuple,
    # ce qui rend le code appelant plus lisible (row["titre"] plutôt que row[0]).
    # open=False : on ouvre explicitement ensuite, pour contrôler le moment
    # (utile avec le lifespan de FastAPI).
    # register_vector sur chaque connexion : c'est ce qui permet à psycopg de convertir
    # une list[float] Python en type `vector` Postgres (et inversement à la lecture),
    # sans quoi il faudrait formater les vecteurs en chaînes "[0.1,0.2,...]" à la main.
    pool = ConnectionPool(
        settings.DATABASE_URL,
        kwargs={"row_factory": dict_row},
        configure=register_vector,
        open=False,
    )
    pool.open()


def close_pool() -> None:
    global pool
    if pool is not None:
        pool.close()
        pool = None


def ping() -> dict:
    """Vérifie que la base répond, que pgvector est installé, et compte les chunks."""
    assert pool is not None, "le pool n'est pas ouvert (open_pool() n'a pas été appelé)"

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()["version"]

            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            pgvector = cur.fetchone()["exists"]

            cur.execute("SELECT count(*) AS count FROM chunks")
            chunks_count = cur.fetchone()["count"]

    return {
        "postgres_version": version,
        "pgvector": pgvector,
        "chunks_count": chunks_count,
    }
