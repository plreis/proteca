from typing import Annotated, List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

INSECURE_SECRET_KEY = "insecure-default-change-in-production"
# Relativo ao diretório de trabalho: no container (WORKDIR /app) vira /app/data/proteca.db,
# onde o Coolify monta o volume persistente (ADR 0003).
DEFAULT_DATABASE_URL = "sqlite:///./data/proteca.db"
EXAMPLE_SECRET_KEYS = {
    INSECURE_SECRET_KEY,
    "troque-esta-chave",
    "exemplo-chave-secreta-alterar-em-producao",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Proteca API"
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    BACKEND_CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:3000",
    ]

    # JWT (Sprint 3)
    SECRET_KEY: str = INSECURE_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SENHA_TESTE_HASH: str = "COLE_AQUI_O_HASH_GERADO"  # Hash de senha para teste (Sprint 3)
    # Banco de dados (Sprint 4): SQLite acessado só pelo SQLModel.
    DATABASE_URL: str = DEFAULT_DATABASE_URL
    SEED_DEMO_DATA: bool = True

    # Gemini: a chave fica só no servidor.
    GEMINI_API_KEY: str | None = None
    # Modelo preferido e, na ordem, os reservas usados quando ele falha (503, 429, 404...).
    # Os "lite" vêm primeiro porque a cota gratuita deles é maior (500 requisições/dia).
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_FALLBACK_MODELS: Annotated[List[str], NoDecode] = [
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.6-flash",
    ]
    GEMINI_TIMEOUT_SECONDS: float = 20.0
    # Voz da intervenção do Proteca (TTS). Cada modelo tem cota diária pequena, por isso o rodízio.
    GEMINI_TTS_MODELS: Annotated[List[str], NoDecode] = [
        "gemini-3.8-flash-tts",
        "gemini-3.8-flash-lite-tts",
        "gemini-3.1-flash-tts-preview",
        "gemini-2.5-flash-preview-tts",
    ]
    GEMINI_TTS_VOICE: str = "Puck"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("GEMINI_FALLBACK_MODELS", "GEMINI_TTS_MODELS", mode="before")
    @classmethod
    def parse_model_list(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            return [model.strip() for model in value.split(",") if model.strip()]
        return value

    @property
    def gemini_text_models(self) -> List[str]:
        """Ordem de tentativa: preferido primeiro, reservas depois, sem repetir."""
        return list(dict.fromkeys([self.GEMINI_MODEL, *self.GEMINI_FALLBACK_MODELS]))

    @field_validator("GEMINI_API_KEY", mode="before")
    @classmethod
    def empty_string_is_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def empty_database_url_is_default(cls, value: str | None) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return DEFAULT_DATABASE_URL
        return value.strip()

    @model_validator(mode="after")
    def require_real_secret_in_production(self) -> "Settings":
        weak = self.SECRET_KEY in EXAMPLE_SECRET_KEYS or len(self.SECRET_KEY) < 32
        if self.ENVIRONMENT == "production" and weak:
            raise ValueError("Defina uma SECRET_KEY forte (32+ caracteres) em produção.")
        return self

    @property
    def ai_enabled(self) -> bool:
        return bool(self.GEMINI_API_KEY)


settings = Settings()
