import httpx
import pytest

from app.core.config import settings
from app.schemas.ai import AILiveGuidanceRequest
from app.services.ai_guidance import generate_live_guidance
from tests.conftest import OBJECTIVE


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": self.text}]}}]}


class FakeClient:
    calls = []

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def post(self, *args, **kwargs):
        FakeClient.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def test_live_guidance_returns_honest_local_fallback_without_key(client):
    response = client.post(
        "/api/v1/ia/live",
        json={
            "session_id": "sess-001",
            "objective": OBJECTIVE,
            "focus": {
                "active_devices": 10,
                "focus_lost_events": 12,
                "safety_alerts": 0,
                "open_incidents": 1,
                "elapsed_minutes": 20,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_mock"] is True
    assert data["model"] == "local-fallback"
    assert data["intervention"]["state"] == "curiosidade"
    assert "não diagnostica" in data["limitations"]


def test_live_guidance_rejects_short_objective(client):
    response = client.post("/api/v1/ia/live", json={"session_id": "s", "objective": "foco"})

    assert response.status_code == 422


def test_session_live_uses_signals_from_the_session(client, open_session):
    session_id = open_session["id"]
    client.post(
        "/api/v1/incidents",
        json={
            "session_id": session_id,
            "device_id": "dev-04",
            "category": "privacidade_exposicao",
            "description": "Tablet usado para fotografar colegas sem autorização.",
        },
    )
    client.post(
        "/api/v1/telemetry",
        json={
            "session_id": session_id,
            "device_id": "dev-03",
            "event_type": "foco_perdido",
            "occurred_at": "2026-11-18T10:00:00-03:00",
        },
    )

    response = client.post(f"/api/v1/sessions/{session_id}/live")

    assert response.status_code == 200
    data = response.json()
    assert data["attention_level"] == "alerta"
    assert data["signals"]["active_devices"] == 2
    assert data["signals"]["focus_lost_events"] == 1
    assert data["signals"]["safety_alerts"] == 1
    assert data["signals"]["incident_categories"] == {"privacidade_exposicao": 1}


def test_session_live_requires_open_session(client):
    assert client.post("/api/v1/sessions/sess-x/live").status_code == 404
    assert client.post("/api/v1/sessions/sess-02/live").status_code == 409


def test_live_guidance_parses_a_successful_gemini_response(monkeypatch):
    FakeClient.calls = []
    text = (
        '{"attention_level":"foco","observed_pattern":"A turma avançou.",'
        '"teacher_suggestions":["Peça uma síntese."],"intervention":null}'
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai_guidance.httpx.Client",
        lambda **kwargs: FakeClient(response=FakeResponse(text)),
    )

    response = generate_live_guidance(
        AILiveGuidanceRequest(session_id="sess-001", objective=OBJECTIVE)
    )

    assert response.model == settings.GEMINI_MODEL
    assert response.is_mock is False
    assert response.observed_pattern == "A turma avançou."
    assert FakeClient.calls[0]["headers"] == {"x-goog-api-key": "test-key"}
    assert "params" not in FakeClient.calls[0]


def test_live_guidance_falls_back_when_gemini_fails(monkeypatch):
    error = httpx.ConnectError(
        "provider unavailable",
        request=httpx.Request("POST", "https://example.com"),
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai_guidance.httpx.Client",
        lambda **kwargs: FakeClient(error=error),
    )

    response = generate_live_guidance(
        AILiveGuidanceRequest(session_id="sess-001", objective=OBJECTIVE)
    )

    assert response.model == "local-fallback"
    assert response.is_mock is True


def test_live_guidance_falls_back_on_invalid_json(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai_guidance.httpx.Client",
        lambda **kwargs: FakeClient(response=FakeResponse("isto não é json")),
    )

    response = generate_live_guidance(
        AILiveGuidanceRequest(session_id="sess-001", objective=OBJECTIVE)
    )

    assert response.is_mock is True


GOOD_GUIDANCE = (
    '{"attention_level":"atenção","observed_pattern":"Parte da turma dispersou.",'
    '"teacher_suggestions":["Retome o objetivo."],"intervention":null}'
)


class GeminiReply:
    def __init__(self, status_code=200, text=GOOD_GUIDANCE):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.com")
            raise httpx.HTTPStatusError(
                "erro do Gemini",
                request=request,
                response=httpx.Response(self.status_code, request=request),
            )

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": self.text}]}}]}


class GeminiByModel:
    """Simula o Gemini respondendo de forma diferente para cada modelo da URL."""

    def __init__(self, replies):
        self.replies = replies
        self.models_called = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def post(self, url, **kwargs):
        model = url.split("/models/")[1].split(":")[0]
        self.models_called.append(model)
        return self.replies[model]


def use_fake_gemini(monkeypatch, replies, models):
    fake = GeminiByModel(replies)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", models[0])
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", models[1:])
    monkeypatch.setattr("app.services.ai_guidance.httpx.Client", lambda **kwargs: fake)
    return fake


def test_live_guidance_uses_next_model_when_first_is_overloaded(monkeypatch):
    fake = use_fake_gemini(
        monkeypatch,
        {"modelo-a": GeminiReply(status_code=503), "modelo-b": GeminiReply()},
        ["modelo-a", "modelo-b"],
    )

    response = generate_live_guidance(
        AILiveGuidanceRequest(session_id="sess-001", objective=OBJECTIVE)
    )

    assert response.is_mock is False
    assert response.model == "modelo-b"
    assert fake.models_called == ["modelo-a", "modelo-b"]


def test_live_guidance_falls_back_locally_after_trying_every_model(monkeypatch):
    fake = use_fake_gemini(
        monkeypatch,
        {
            "sobrecarregado": GeminiReply(status_code=503),
            "sem-cota": GeminiReply(status_code=429),
            "removido": GeminiReply(status_code=404),
        },
        ["sobrecarregado", "sem-cota", "removido"],
    )

    response = generate_live_guidance(
        AILiveGuidanceRequest(session_id="sess-001", objective=OBJECTIVE)
    )

    assert response.is_mock is True
    assert response.model == "local-fallback"
    assert fake.models_called == ["sobrecarregado", "sem-cota", "removido"]


def test_live_guidance_brings_the_proteca_speech_from_gemini(monkeypatch):
    FakeClient.calls = []
    text = (
        '{"attention_level":"atenção","observed_pattern":"Parte da turma dispersou.",'
        '"teacher_suggestions":["Retome o objetivo."],'
        '"intervention":{"state":"curiosidade","title":"Proteca tem uma pergunta",'
        '"message":"Uma pista pode ajudar a turma a reencontrar o objetivo.",'
        '"prompt":"Que parte do objetivo você explica com um exemplo?",'
        '"speech":"Turma, eu tenho uma pergunta: quem explica o objetivo com um exemplo?"}}'
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai_guidance.httpx.Client",
        lambda **kwargs: FakeClient(response=FakeResponse(text)),
    )

    response = generate_live_guidance(
        AILiveGuidanceRequest(session_id="sess-001", objective=OBJECTIVE)
    )

    assert response.is_mock is False
    assert response.intervention.speech == (
        "Turma, eu tenho uma pergunta: quem explica o objetivo com um exemplo?"
    )
    intervention_schema = FakeClient.calls[0]["json"]["generationConfig"]["responseSchema"][
        "properties"
    ]["intervention"]
    assert "speech" in intervention_schema["properties"]
    assert "speech" in intervention_schema["required"]
    assert "speech" in FakeClient.calls[0]["json"]["contents"][0]["parts"][0]["text"]


@pytest.mark.parametrize(
    ("focus", "state"),
    [
        ({"safety_alerts": 1}, "alerta"),
        ({"active_devices": 2, "focus_lost_events": 5}, "curiosidade"),
        ({}, "acolhimento"),
    ],
)
def test_fallback_intervention_has_a_short_proteca_speech(client, focus, state):
    response = client.post(
        "/api/v1/ia/live",
        json={"session_id": "sess-001", "objective": OBJECTIVE, "focus": focus},
    )

    intervention = response.json()["intervention"]
    assert intervention["state"] == state
    assert intervention["speech"]
    assert len(intervention["speech"].split()) <= 25
