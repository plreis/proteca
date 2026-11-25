from fastapi import APIRouter, HTTPException, Response

from app.core.dependencies import RepositoryDependency, class_voices
from app.schemas.turma import ClassScreenResponse
from app.services.class_screen import build_class_screen

router = APIRouter(prefix="/turma", tags=["Tela da turma"])


@router.get("/{codigo}", response_model=ClassScreenResponse, summary="Tela da turma (pública)")
def class_screen(codigo: str, repository: RepositoryDependency):
    state = repository.get_class_screen_state(codigo)
    return build_class_screen(state, class_voices)


@router.get("/{codigo}/voz", summary="Voz do Proteca da intervenção atual (pública)")
def class_voice(codigo: str, repository: RepositoryDependency):
    state = repository.get_class_screen_state(codigo)
    voice = class_voices.get(state.session_id, state.broadcast_at)
    if voice is None:
        raise HTTPException(status_code=404, detail="Não há voz para a intervenção atual.")
    return Response(
        content=voice.wav,
        media_type="audio/wav",
        headers={"X-Proteca-Voice-Model": voice.model},
    )
