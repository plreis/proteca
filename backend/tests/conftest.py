import pytest
from fastapi.testclient import TestClient

from app.auth.middleware import get_current_user
from app.core.config import settings
from app.main import app
from app.schemas.auth import UserPublic, UserRole

OBJECTIVE = "Compreender como proteger dados pessoais na escola."

# Os testes de regra de negócio rodam como um professor já autenticado.
# O login é coberto em test_auth.py.
TEST_PROFESSOR = UserPublic(
    id="usr-teste",
    username="professor.teste@proteca.local",
    full_name="Professor de Teste",
    role=UserRole.PROFESSOR,
)


@pytest.fixture(autouse=True)
def no_real_gemini(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)


@pytest.fixture(autouse=True)
def in_memory_database(monkeypatch):
    # Cada TestClient sobe a API com um SQLite novo em memória, semeado com a carga inicial.
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite://")
    monkeypatch.setattr(settings, "SEED_DEMO_DATA", True)


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: TEST_PROFESSOR
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def open_session(client):
    response = client.post(
        "/api/v1/sessions",
        json={
            "classroom_id": "cls-8b",
            "teacher_name": "Profa. Teste",
            "objective": OBJECTIVE,
            "device_ids": ["dev-03", "dev-04"],
        },
    )
    assert response.status_code == 201
    return response.json()
