"""Tela da turma: monta a resposta pública e guarda a voz já sintetizada de cada sessão."""

from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from app.schemas.ai import ProtecaIntervention
from app.schemas.turma import ClassScreenResponse, ClassScreenState
from app.services.voice import synthesize_speech


@dataclass(frozen=True)
class CachedVoice:
    broadcast_at: datetime
    wav: bytes
    model: str


class ClassVoiceCache:
    """Voz do Proteca da intervenção atual de cada sessão, em memória (chave: session_id).

    É preenchida em segundo plano quando o professor envia a intervenção. A rota pública
    só lê daqui e nunca chama o Gemini, para que a tela da turma não gaste cota. Cada
    áudio vale só para o broadcast_at em que foi gerado.
    """

    def __init__(self) -> None:
        self._items: dict[str, CachedVoice] = {}
        self._lock = Lock()

    def prepare(self, session_id: str, broadcast_at: datetime, text: str) -> None:
        speech = synthesize_speech(text)
        with self._lock:
            current = self._items.get(session_id)
            if current is not None and current.broadcast_at > broadcast_at:
                return  # uma intervenção mais nova já tem a própria voz
            if speech is None:
                self._items.pop(session_id, None)
            else:
                self._items[session_id] = CachedVoice(broadcast_at, speech.wav, speech.model)

    def get(self, session_id: str, broadcast_at: datetime | None) -> CachedVoice | None:
        if broadcast_at is None:
            return None
        with self._lock:
            voice = self._items.get(session_id)
        return voice if voice is not None and voice.broadcast_at == broadcast_at else None

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._items.pop(session_id, None)


def speech_text(intervention: ProtecaIntervention) -> str:
    """O que a voz do Proteca lê: a fala, ou mensagem e pergunta quando não há fala."""
    return intervention.speech or f"{intervention.message} {intervention.prompt}"


def build_class_screen(state: ClassScreenState, voices: ClassVoiceCache) -> ClassScreenResponse:
    return ClassScreenResponse(
        class_code=state.class_code,
        objective=state.objective,
        session_status=state.session_status,
        intervention=state.intervention,
        broadcast_at=state.broadcast_at,
        audio_ready=voices.get(state.session_id, state.broadcast_at) is not None,
    )
