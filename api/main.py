import logging
from contextlib import asynccontextmanager

from elevenlabs.core.api_error import ApiError as ElevenLabsApiError
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors

from api import db as dbmod
from api.config import settings
from api.routers import analytics, sessions
from api.services.voice import stt, tts
from api.services.llm import LANGUAGES, RETRYABLE_CODES

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if dbmod.engine is not None:
        await dbmod.init_db()
    else:
        log.warning("DATABASE_URL not set — database endpoints will fail")
    yield


app = FastAPI(title="Language Learning API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upstream failures become readable JSON errors. Unlike a bare 500, these pass through the CORS
# middleware, so the browser shows the message instead of a generic "Failed to fetch".
@app.exception_handler(genai_errors.APIError)
async def gemini_error(request: Request, exc: genai_errors.APIError):
    log.error("Gemini error %s: %s", exc.code, exc)
    if exc.code in RETRYABLE_CODES:
        return JSONResponse(status_code=503, content={"detail": "The AI tutor is busy right now. Please try again in a moment."})
    return JSONResponse(status_code=502, content={"detail": f"Gemini error ({exc.code}): {str(exc)[:200]}"})


@app.exception_handler(ElevenLabsApiError)
async def elevenlabs_error(request: Request, exc: ElevenLabsApiError):
    code = exc.status_code or 502
    log.error("ElevenLabs error %s: %s", code, str(exc.body)[:300])
    # ElevenLabs explains most failures itself ({"detail": {"message": ...}}); surface that.
    body = exc.body.get("detail") if isinstance(exc.body, dict) else None
    reason = body.get("message") if isinstance(body, dict) else body
    if code == 429:
        detail = "ElevenLabs rate limit or quota reached. Please try again shortly."
    elif code in (401, 403) or (isinstance(reason, str) and "api key" in reason.lower()):
        detail = f"ElevenLabs rejected the API key: {reason or 'check ELEVENLABS_API_KEY in .env'}"
    else:
        detail = f"Speech service error ({code}): {reason}" if isinstance(reason, str) else f"Speech service error ({code})."
    return JSONResponse(status_code=502, content={"detail": detail})


app.include_router(sessions.router)
app.include_router(analytics.router)


@app.get("/config")
async def app_config():
    """What config.toml and the ElevenLabs modules currently resolve to, so the UI can show it."""
    name = settings.default_language.strip().lower()
    code = next((c for c, n in LANGUAGES.items() if name in (c, n.lower())), None)
    return {
        "language": code,
        "language_name": settings.default_language,
        "level": settings.default_level or None,
        "gemini_model": settings.gemini_model,
        "elevenlabs": {
            "voice_id": tts.VOICE_ID,
            "stt_model": stt.MODEL_ID,
            "tts_model": tts.MODEL_ID,
        },
    }


@app.get("/health")
async def health():
    return {
        "ok": True,
        "db": dbmod.engine is not None,
        "gemini": bool(settings.gemini_api_key),
        "elevenlabs": bool(settings.elevenlabs_api_key),
    }
