from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # Hosted Postgres with pgvector (Neon / Supabase). Plain postgres:// URLs are fine.
    database_url: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    # Tried once if the primary model keeps returning overload/server errors. Empty disables it.
    gemini_fallback_model: str = "gemini-3.7-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    elevenlabs_api_key: str = ""
    elevenlabs_stt_model: str = "scribe_v1"
    elevenlabs_tts_model: str = "eleven_flash_v2_5"
    # "Rachel" — a default multilingual voice; override per deployment.
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
