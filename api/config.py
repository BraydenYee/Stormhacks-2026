import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


def _load_toml() -> dict:
    """Teammates' shared settings file (also used by gemini_chat.py). Missing or invalid → defaults."""
    try:
        with (ROOT / "config.toml").open("rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


TOML = _load_toml()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # Hosted Postgres with pgvector (Neon / Supabase). Plain postgres:// URLs are fine.
    database_url: str = ""

    gemini_api_key: str = ""
    # config.toml sets the default; a GEMINI_MODEL env var still wins.
    gemini_model: str = TOML.get("model", "gemini-3.8-flash")
    # Tried once if the primary model keeps returning overload/server errors. Empty disables it.
    gemini_fallback_model: str = "gemini-3.7-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    # Defaults for new learners, from config.toml: e.g. "Japanese" and "beginner" / "B1".
    default_language: str = TOML.get("language", "Spanish")
    default_level: str = TOML.get("level", "")

    elevenlabs_api_key: str = ""
    elevenlabs_stt_model: str = "scribe_v2"
    elevenlabs_tts_model: str = "eleven_flash_v2_5"
    # Voice and voice settings from ElevenLabs/textToSpeech.py.
    elevenlabs_voice_id: str = "r1KmysJdVYZjJCm4mL3b"
    elevenlabs_stability: float = 0.0
    elevenlabs_similarity_boost: float = 1.0
    elevenlabs_style: float = 0.0
    elevenlabs_speaker_boost: bool = True

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
