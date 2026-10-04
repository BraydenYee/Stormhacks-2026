import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {"language": "English", "level": "intermediate", "model": "gemini-3.8-flash"}


def load_config() -> dict:
    # config.toml (model, language, level) at the project root; missing file falls back to DEFAULTS.
    path = ROOT / "config.toml"
    if not path.exists():
        return dict(DEFAULTS)
    with path.open("rb") as f:
        return {**DEFAULTS, **tomllib.load(f)}


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

    # Voice, voice settings and models live in api/services/Elevenlabs/.
    elevenlabs_api_key: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
