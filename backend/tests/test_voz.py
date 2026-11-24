import base64
import io
import wave

import httpx

from app.core.config import settings

MESSAGE = "Vamos retomar o objetivo da aula juntos?"
PCM_24KHZ = b"\x00\x01" * 2400  # 2400 amostras de 16 bits = 0,1 s a 24 kHz


class TTSReply:
    def __init__(self, status_code=200, pcm=PCM_24KHZ):
        self.status_code = status_code
        self.pcm = pcm

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.com")
            raise httpx.HTTPStatusError(
                "erro do Gemini",
                request=request,
                response=httpx.Response(self.status_code, request=request),
            )

    def json(self):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/L16;codec=pcm;rate=24000",
                                    "data": base64.b64encode(self.pcm).decode(),
                                }
                            }
                        ]
                    }
                }
            ]
        }


class TTSByModel:
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


def use_fake_tts(monkeypatch, replies):
    fake = TTSByModel(replies)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_TTS_MODELS", list(replies))
    monkeypatch.setattr("app.services.voice.httpx.Client", lambda **kwargs: fake)
    return fake


def test_voice_returns_wav_from_first_tts_model_that_works(client, monkeypatch):
    fake = use_fake_tts(
        monkeypatch,
        {"tts-sobrecarregado": TTSReply(status_code=503), "tts-ok": TTSReply()},
    )

    response = client.post("/api/v1/ia/voz", json={"text": MESSAGE})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["x-proteca-voice-model"] == "tts-ok"
    assert fake.models_called == ["tts-sobrecarregado", "tts-ok"]
    with wave.open(io.BytesIO(response.content)) as audio:
        assert audio.getframerate() == 24000
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getnframes() == 2400


def test_voice_is_503_when_every_tts_model_fails(client, monkeypatch):
    use_fake_tts(
        monkeypatch,
        {"tts-sem-cota": TTSReply(status_code=429), "tts-sobrecarregado": TTSReply(status_code=503)},
    )

    response = client.post("/api/v1/ia/voz", json={"text": MESSAGE})

    assert response.status_code == 503


def test_voice_requires_login(client):
    from app.auth.middleware import get_current_user
    from app.main import app

    app.dependency_overrides.pop(get_current_user)

    response = client.post("/api/v1/ia/voz", json={"text": MESSAGE})

    assert response.status_code == 401
