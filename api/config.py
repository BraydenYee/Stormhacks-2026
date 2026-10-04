from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from api.services.gemini_chat import load_config

ROOT = Path(__file__).resolve().parent.parent

# config.toml (model, language, level), shared with the gemini_chat.py CLI and loaded by its loader.
TOML = load_config()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # Hosted Postgres with pgvector (Neon / Supabase). Plain postgres:// URLs are fine.
    database_url: str = ""

    gemini_api_key: str = ""
    # config.toml sets the default; a GEMINI_MODEL env var still wins.
    gemini_model: str = TOML["model"]
    # Tried once if the primary model keeps returning overload/server errors. Empty disables it.
    gemini_fallback_model: str = "gemini-3.7-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    # Defaults for new learners, from config.toml: e.g. "Japanese" and "beginner" / "B1".
    default_language: str = TOML["language"]
    default_level: str = TOML["level"]

    # Voice, voice settings and models live in api/services/elevenlabs/.
    elevenlabs_api_key: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
