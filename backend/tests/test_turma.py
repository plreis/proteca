import io
import wave

import pytest

from app.auth.middleware import get_current_user
from app.main import app
from tests.test_voz import TTSReply, use_fake_tts

INTERVENTION = {
    "state": "curiosidade",
    "title": "Proteca tem uma pergunta",
    "message": "Uma pista pode ajudar a turma a reencontrar o objetivo da aula.",
    "prompt": "Que parte do objetivo você consegue explicar com um exemplo?",
    "speech": "Turma, eu tenho uma pergunta: quem explica o nosso objetivo com um exemplo?",
}
SCREEN_FIELDS = {
    "class_code",
    "objective",
    "session_status",
    "intervention",
    "broadcast_at",
    "audio_ready",
}


def send_to_class(client, session_id="sess-01", intervention=INTERVENTION):
    return client.post(
        f"/api/v1/sessions/{session_id}/turma",
        json={"intervention": intervention},
    )


def log_out(client):
    app.dependency_overrides.pop(get_current_user)


@pytest.fixture
def tts_ok(monkeypatch):
    return use_fake_tts(monkeypatch, {"tts-ok": TTSReply()})


def test_class_screen_shows_the_intervention_the_professor_sent(client, tts_ok):
    sent = send_to_class(client)

    screen = client.get("/api/v1/turma/AULA8B")

    assert sent.status_code == 200
    assert screen.status_code == 200
    data = screen.json()
    assert set(data) == SCREEN_FIELDS
    assert data["class_code"] == "AULA8B"
    assert data["objective"].startswith("Pesquisa orientada de Geografia")
    assert data["session_status"] == "aberta"
    assert data["intervention"] == INTERVENTION
    assert data["broadcast_at"] == sent.json()["broadcast_at"]
    assert data["broadcast_at"].endswith("Z")


def test_class_screen_never_exposes_teacher_devices_incidents_or_ids(client, tts_ok):
    send_to_class(client)

    body = client.get("/api/v1/turma/AULA8B").text

    for forbidden in ("Carlos", "sess-01", "cls-7a", "sch-01", "dev-0", "DEV-", "inc-0"):
        assert forbidden not in body


def test_class_screen_before_any_intervention(client):
    data = client.get("/api/v1/turma/AULA8B").json()

    assert data["intervention"] is None
    assert data["broadcast_at"] is None
    assert data["audio_ready"] is False


def test_class_code_is_case_insensitive(client):
    assert client.get("/api/v1/turma/aula8b").status_code == 200
    assert client.get("/api/v1/turma/aula8b").json()["class_code"] == "AULA8B"


def test_unknown_class_code_is_404(client):
    assert client.get("/api/v1/turma/ZZZZZZ").status_code == 404
    assert client.get("/api/v1/turma/ZZZZZZ/voz").status_code == 404


def test_new_session_code_opens_its_class_screen(client, open_session):
    data = client.get(f"/api/v1/turma/{open_session['class_code']}").json()

    assert data["objective"] == open_session["objective"]
    assert data["session_status"] == "aberta"


def test_closed_session_shows_no_intervention(client, open_session, tts_ok):
    code = open_session["class_code"]
    send_to_class(client, open_session["id"])
    client.patch(
        f"/api/v1/sessions/{open_session['id']}/close",
        json={"justification": "Aula concluída e aparelhos conferidos."},
    )

    data = client.get(f"/api/v1/turma/{code}").json()
    closed_demo = client.get("/api/v1/turma/AULA7A").json()

    for screen in (data, closed_demo):
        assert screen["session_status"] == "encerrada"
        assert screen["intervention"] is None
        assert screen["audio_ready"] is False
    assert client.get(f"/api/v1/turma/{code}/voz").status_code == 404


def test_sending_to_unknown_or_closed_session(client):
    assert send_to_class(client, "sess-x").status_code == 404
    assert send_to_class(client, "sess-02").status_code == 409


def test_sending_validates_the_intervention(client):
    too_long = {**INTERVENTION, "speech": "fala " * 100}

    assert send_to_class(client, intervention=too_long).status_code == 422


def test_class_routes_are_public(client):
    log_out(client)

    assert client.get("/api/v1/turma/AULA8B").status_code == 200
    assert client.get("/api/v1/turma/AULA8B/voz").status_code == 404


def test_sending_to_the_class_requires_login(client):
    log_out(client)

    assert send_to_class(client).status_code == 401
    assert client.delete("/api/v1/sessions/sess-01/turma").status_code == 401


def test_class_voice_is_ready_after_sending(client, monkeypatch):
    fake = use_fake_tts(monkeypatch, {"tts-sobrecarregado": TTSReply(503), "tts-ok": TTSReply()})
    before = client.get("/api/v1/turma/AULA8B/voz")

    sent = send_to_class(client)
    screen = client.get("/api/v1/turma/AULA8B").json()
    voice = client.get("/api/v1/turma/AULA8B/voz")

    assert before.status_code == 404
    assert sent.json()["audio_ready"] is False  # a voz é preparada depois da resposta
    assert screen["audio_ready"] is True
    assert voice.status_code == 200
    assert voice.headers["content-type"] == "audio/wav"
    assert voice.headers["x-proteca-voice-model"] == "tts-ok"
    with wave.open(io.BytesIO(voice.content)) as audio:
        assert audio.getnframes() == 2400
    # Só a fala do Proteca vai para o TTS.
    assert [body["contents"][0]["parts"][0]["text"] for body in fake.bodies][-1] == (
        INTERVENTION["speech"]
    )


def test_class_voice_reads_message_and_prompt_when_there_is_no_speech(client, monkeypatch):
    fake = use_fake_tts(monkeypatch, {"tts-ok": TTSReply()})
    without_speech = {key: value for key, value in INTERVENTION.items() if key != "speech"}

    send_to_class(client, intervention=without_speech)

    assert fake.bodies[0]["contents"][0]["parts"][0]["text"] == (
        f"{INTERVENTION['message']} {INTERVENTION['prompt']}"
    )
    assert client.get("/api/v1/turma/AULA8B").json()["intervention"]["speech"] is None


def test_public_voice_route_never_calls_gemini(client, tts_ok):
    client.get("/api/v1/turma/AULA8B/voz")
    client.get("/api/v1/turma/AULA8B")

    assert tts_ok.models_called == []


def test_class_voice_is_not_ready_when_synthesis_fails(client, monkeypatch):
    use_fake_tts(monkeypatch, {"tts-sem-cota": TTSReply(429)})

    send_to_class(client)

    assert client.get("/api/v1/turma/AULA8B").json()["audio_ready"] is False
    assert client.get("/api/v1/turma/AULA8B/voz").status_code == 404


def test_new_intervention_does_not_reuse_the_previous_voice(client, monkeypatch):
    use_fake_tts(monkeypatch, {"tts-ok": TTSReply()})
    send_to_class(client)
    use_fake_tts(monkeypatch, {"tts-sem-cota": TTSReply(429)})

    send_to_class(client, intervention={**INTERVENTION, "speech": "Outra fala para a turma."})

    screen = client.get("/api/v1/turma/AULA8B").json()
    assert screen["intervention"]["speech"] == "Outra fala para a turma."
    assert screen["audio_ready"] is False
    assert client.get("/api/v1/turma/AULA8B/voz").status_code == 404


def test_removing_the_intervention_clears_the_class_screen(client, tts_ok):
    send_to_class(client)

    removed = client.delete("/api/v1/sessions/sess-01/turma")
    screen = client.get("/api/v1/turma/AULA8B").json()

    assert removed.status_code == 204
    assert screen["intervention"] is None
    assert screen["broadcast_at"] is None
    assert screen["audio_ready"] is False
    assert client.get("/api/v1/turma/AULA8B/voz").status_code == 404


def test_removing_from_unknown_session_is_404(client):
    assert client.delete("/api/v1/sessions/sess-x/turma").status_code == 404
