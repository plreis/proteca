from fastapi import APIRouter, Request

from app.core.config import settings

router = APIRouter(tags=["Saúde"])


@router.get("/health")
def health_check(request: Request):
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "storage": request.app.state.engine.dialect.name,
        "ai_provider": "gemini" if settings.ai_enabled else "local-fallback",
        "ai_model": settings.GEMINI_MODEL if settings.ai_enabled else None,
    }
