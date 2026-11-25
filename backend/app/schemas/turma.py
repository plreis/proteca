from datetime import datetime

from pydantic import BaseModel

from app.schemas.ai import ProtecaIntervention
from app.schemas.sessions import SessionStatus


class ClassBroadcastRequest(BaseModel):
    """Intervenção que o professor decidiu enviar para a tela da turma."""

    intervention: ProtecaIntervention


class ClassScreenResponse(BaseModel):
    """Tela da turma, pública e sem login (ADR 0004).

    Só o objetivo da aula e a intervenção enviada. Nunca inclui o nome do professor,
    dispositivos, ocorrências ou ids internos.
    """

    class_code: str
    objective: str
    session_status: SessionStatus
    intervention: ProtecaIntervention | None = None
    broadcast_at: datetime | None = None
    audio_ready: bool = False


class ClassScreenState(BaseModel):
    """Uso interno: o session_id serve só para achar a voz no cache e nunca sai pela API."""

    session_id: str
    class_code: str
    objective: str
    session_status: SessionStatus
    intervention: ProtecaIntervention | None = None
    broadcast_at: datetime | None = None
