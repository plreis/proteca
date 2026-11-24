from fastapi import APIRouter, HTTPException, Response, status

from app.schemas.ai import AILiveGuidanceRequest, AILiveGuidanceResponse, VoiceRequest
from app.services.ai_guidance import generate_live_guidance
from app.services.voice import synthesize_speech

router = APIRouter(prefix="/ia", tags=["Inteligência pedagógica"])


@router.post(
    "/live",
    response_model=AILiveGuidanceResponse,
    summary="Proteca Live com sinais informados",
    description=(
        "Versão sem estado: o cliente envia objetivo e sinais agregados. "
        "No fluxo da aplicação, prefira POST /sessions/{session_id}/live."
    ),
)
def live_guidance(data: AILiveGuidanceRequest):
    return generate_live_guidance(data)


@router.post(
    "/voz",
    response_class=Response,
    summary="Voz do Proteca",
    description=(
        "Lê em voz alta a mensagem de intervenção usando os modelos TTS do Gemini em rodízio. "
        "Devolve audio/wav e o modelo usado no cabeçalho X-Proteca-Voice-Model. "
        "Com todos os modelos indisponíveis responde 503, e o site usa a voz do navegador."
    ),
    responses={200: {"content": {"audio/wav": {}}}, 503: {"description": "Nenhum modelo de voz disponível"}},
)
def voice(data: VoiceRequest):
    speech = synthesize_speech(data.text)
    if speech is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voz do Gemini indisponível agora.",
        )
    return Response(
        content=speech.wav,
        media_type="audio/wav",
        headers={"X-Proteca-Voice-Model": speech.model},
    )
