import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors

from api import db as dbmod
from api.config import settings
from api.routers import analytics, sessions
from api.services.llm import LANGUAGES, RETRYABLE_CODES

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if dbmod.engine is not None:
        await dbmod.init_db()
        try:
            from api.seed_topics import seed

            n = await seed()
            if n:
                log.info("seeded %d topics", n)
        except Exception:
            log.exception("topic seeding skipped (is GEMINI_API_KEY set?)")
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


@app.exception_handler(httpx.HTTPStatusError)
async def elevenlabs_error(request: Request, exc: httpx.HTTPStatusError):
    code = exc.response.status_code
    log.error("ElevenLabs error %s: %s", code, exc.response.text[:300])
    # ElevenLabs explains most failures itself ({"detail": {"message": ...}}); surface that.
    try:
        body = exc.response.json().get("detail")
        reason = body.get("message") if isinstance(body, dict) else body
    except Exception:
        reason = None
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
    """What the teammates' config files currently resolve to, so the UI (and they) can see it."""
    name = settings.default_language.strip().lower()
    code = next((c for c, n in LANGUAGES.items() if name in (c, n.lower())), None)
    return {
        "language": code,
        "language_name": settings.default_language,
        "level": settings.default_level or None,
        "gemini_model": settings.gemini_model,
        "elevenlabs": {
            "voice_id": settings.elevenlabs_voice_id,
            "stt_model": settings.elevenlabs_stt_model,
            "tts_model": settings.elevenlabs_tts_model,
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
