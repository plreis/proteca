from fastapi import APIRouter, BackgroundTasks, Response, status

from app.core.dependencies import RepositoryDependency, class_voices
from app.schemas.ai import AILiveGuidanceResponse
from app.schemas.sessions import (
    SessionClose,
    SessionCreate,
    SessionResponse,
    SessionStatus,
)
from app.schemas.turma import ClassBroadcastRequest, ClassScreenResponse
from app.services.class_screen import build_class_screen, speech_text
from app.services.ai_guidance import generate_live_guidance
from app.services.session_signals import build_live_request

router = APIRouter(prefix="/sessions", tags=["Sessões"])


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    repository: RepositoryDependency,
    session_status: SessionStatus | None = None,
):
    return repository.list_sessions(status=session_status)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(data: SessionCreate, repository: RepositoryDependency):
    return repository.create_session(data)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, repository: RepositoryDependency):
    return repository.get_session(session_id)


@router.patch("/{session_id}/close", response_model=SessionResponse)
def close_session(
    session_id: str,
    data: SessionClose,
    repository: RepositoryDependency,
):
    return repository.close_session(session_id, data.justification)


@router.post(
    "/{session_id}/live",
    response_model=AILiveGuidanceResponse,
    tags=["Inteligência pedagógica"],
    summary="Proteca Live da sessão",
    description=(
        "Calcula sinais agregados da sessão (telemetria e ocorrências abertas) e pede ao "
        "Gemini uma orientação pedagógica. Sem chave ou com falha do provedor, devolve o "
        "fallback local com is_mock=true."
    ),
)
def session_live(session_id: str, repository: RepositoryDependency):
    session = repository.get_open_session(session_id)
    return generate_live_guidance(build_live_request(repository, session))


@router.post(
    "/{session_id}/turma",
    response_model=ClassScreenResponse,
    tags=["Tela da turma"],
    summary="Enviar intervenção à tela da turma",
)
def send_to_class(
    session_id: str,
    data: ClassBroadcastRequest,
    repository: RepositoryDependency,
    background: BackgroundTasks,
):
    broadcast_at = repository.set_broadcast(session_id, data.intervention)
    # A voz é preparada depois da resposta; a tela pública só lê o cache.
    background.add_task(
        class_voices.prepare, session_id, broadcast_at, speech_text(data.intervention)
    )
    state = repository.get_class_screen_state(repository.get_session(session_id).class_code)
    return build_class_screen(state, class_voices)


@router.delete(
    "/{session_id}/turma",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tela da turma"],
    summary="Limpar a tela da turma",
)
def clear_class_screen(session_id: str, repository: RepositoryDependency):
    repository.clear_broadcast(session_id)
    class_voices.clear(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
