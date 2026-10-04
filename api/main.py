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
from api.services.llm import RETRYABLE_CODES

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
    if code in (401, 403):
        detail = "ElevenLabs rejected the API key (or the key lacks access to this feature)."
    elif code == 429:
        detail = "ElevenLabs rate limit or quota reached. Please try again shortly."
    else:
        detail = f"Speech service error ({code})."
    return JSONResponse(status_code=502, content={"detail": detail})


app.include_router(sessions.router)
app.include_router(analytics.router)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "db": dbmod.engine is not None,
        "gemini": bool(settings.gemini_api_key),
        "elevenlabs": bool(settings.elevenlabs_api_key),
    }
