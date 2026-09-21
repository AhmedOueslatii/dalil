"""Test du endpoint /health."""
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    # `with` déclenche le lifespan (open_pool/close_pool) autour du test,
    # sinon le pool ne serait jamais ouvert et la requête échouerait.
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["pgvector"] is True
