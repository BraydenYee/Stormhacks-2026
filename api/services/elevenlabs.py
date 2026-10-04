"""ElevenLabs speech-to-text and text-to-speech over plain HTTP."""

import httpx

from api.config import settings

BASE = "https://api.elevenlabs.io/v1"
_client = httpx.AsyncClient(timeout=60)


def _headers() -> dict:
    if not settings.elevenlabs_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    return {"xi-api-key": settings.elevenlabs_api_key}


async def transcribe(audio: bytes, filename: str, content_type: str) -> dict:
    """Returns {"text", "language_code", "words": [{"text","start","end","type"}]}."""
    resp = await _client.post(
        f"{BASE}/speech-to-text",
        headers=_headers(),
        data={"model_id": settings.elevenlabs_stt_model, "timestamps_granularity": "word"},
        files={"file": (filename, audio, content_type)},
    )
    resp.raise_for_status()
    body = resp.json()
    return {
        "text": (body.get("text") or "").strip(),
        "language_code": body.get("language_code"),
        "words": body.get("words") or [],
    }


async def synthesize(text: str, speed: float = 1.0) -> bytes:
    """Returns MP3 bytes. `speed` is clamped to ElevenLabs' supported 0.7–1.2."""
    resp = await _client.post(
        f"{BASE}/text-to-speech/{settings.elevenlabs_voice_id}",
        headers=_headers(),
        params={"output_format": "mp3_44100_128"},
        json={
            "text": text,
            "model_id": settings.elevenlabs_tts_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": max(0.7, min(1.2, speed)),
            },
        },
    )
    resp.raise_for_status()
    return resp.content
