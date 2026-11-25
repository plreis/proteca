from fastapi.testclient import TestClient

from app.auth.middleware import get_current_user
from app.core.config import settings
from app.main import app
from tests.conftest import OBJECTIVE, TEST_PROFESSOR


def test_session_survives_api_restart_with_the_same_sqlite_file(tmp_path, monkeypatch):
    # O diretório ainda não existe: a API cria ao iniciar, como acontece em /app/data.
    db_file = tmp_path / "data" / "proteca.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file}")
    app.dependency_overrides[get_current_user] = lambda: TEST_PROFESSOR

    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/sessions",
                json={
                    "classroom_id": "cls-8b",
                    "teacher_name": "Profa. Teste",
                    "objective": OBJECTIVE,
                    "device_ids": ["dev-03"],
                },
            )
        # Sair do TestClient encerra a API e descarta o engine.
        assert db_file.exists()

        with TestClient(app) as client:
            again = client.get(f"/api/v1/sessions/{created.json()['id']}")
            devices = client.get("/api/v1/devices").json()
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert again.status_code == 200
    assert again.json() == created.json()
    # A carga inicial não se repete num banco que já tem dados.
    assert len(devices) == 6
    assert {item["id"]: item["status"] for item in devices}["dev-03"] == "em_uso"
