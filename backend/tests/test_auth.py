import pytest
from pwdlib import PasswordHash

from app.core.config import settings

DEMO_USERNAME = "professor@proteca.local"
DEMO_PASSWORD = "senha-de-teste-123"


@pytest.fixture
def demo_hash(request, monkeypatch):
    """SENHA_TESTE_HASH da execução; por padrão, o hash válido de DEMO_PASSWORD."""
    value = getattr(request, "param", None)
    if value is None:
        value = PasswordHash.recommended().hash(DEMO_PASSWORD)
    monkeypatch.setattr(settings, "SENHA_TESTE_HASH", value)
    return value


@pytest.fixture
def client(demo_hash, client):
    # O usuário de demonstração é gravado no banco quando a API sobe, com o hash
    # configurado naquele momento. Por isso o hash é definido antes do TestClient.
    return client


def login(client, username, password):
    return client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )


def test_login_returns_bearer_token_for_demo_professor(client):
    response = login(client, DEMO_USERNAME, DEMO_PASSWORD)

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


@pytest.mark.parametrize(
    "demo_hash",
    [
        "COLE_AQUI_O_HASH_GERADO",  # variável não definida (valor padrão)
        "",  # variável definida vazia
        "=19=65536,t=3,p=4=corrompido",  # "$" interpretado pelo painel de deploy
    ],
    indirect=True,
)
def test_login_is_401_when_demo_hash_is_misconfigured(client, demo_hash):
    response = login(client, DEMO_USERNAME, DEMO_PASSWORD)

    assert response.status_code == 401


def test_login_is_401_with_wrong_password(client):
    response = login(client, DEMO_USERNAME, "senha-errada")

    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário ou senha inválidos."


def test_token_identifies_demo_professor_stored_in_the_database(client):
    from app.auth.middleware import get_current_user
    from app.main import app

    app.dependency_overrides.pop(get_current_user)
    token = login(client, DEMO_USERNAME, DEMO_PASSWORD).json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": "usr-professor-01",
        "username": DEMO_USERNAME,
        "full_name": "Professor Demonstração",
        "role": "professor",
        "disabled": False,
    }
