import base64
import io
import logging
import re
import wave
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_SAMPLE_RATE = 24000


@dataclass
class SpeechAudio:
    wav: bytes
    model: str


def _pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """O Gemini devolve PCM 16 bits mono sem cabeçalho; o navegador toca WAV."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(pcm)
    return buffer.getvalue()


def _sample_rate(mime_type: str) -> int:
    match = re.search(r"rate=(\d+)", mime_type)
    return int(match.group(1)) if match else DEFAULT_SAMPLE_RATE


def synthesize_speech(text: str) -> SpeechAudio | None:
    """Lê o texto com o primeiro modelo TTS que responder. None = nenhum disponível."""
    if not settings.GEMINI_API_KEY:
        return None

    body = {
        # Só a fala: o modelo TTS lê em voz alta qualquer instrução colocada aqui.
        # O tom vem da voz escolhida (GEMINI_TTS_VOICE) e do próprio texto.
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": settings.GEMINI_TTS_VOICE}}
            },
        },
    }

    with httpx.Client(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
        for model in settings.GEMINI_TTS_MODELS:
            try:
                response = client.post(
                    GEMINI_URL.format(model=model),
                    headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                    json=body,
                )
                response.raise_for_status()
                inline = response.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
                pcm = base64.b64decode(inline["data"])
                return SpeechAudio(
                    wav=_pcm_to_wav(pcm, _sample_rate(inline.get("mimeType", ""))),
                    model=model,
                )
            except httpx.HTTPStatusError as error:
                logger.warning(
                    "TTS respondeu HTTP %s para o modelo %s; tentando o próximo.",
                    error.response.status_code,
                    model,
                )
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
                logger.warning("Falha no TTS %s (%s); tentando o próximo.", model, type(error).__name__)
    return None
