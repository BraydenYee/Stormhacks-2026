import asyncio
import base64
import logging
import uuid
from collections import Counter

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from api import db as dbmod
from api.config import settings
from api.db import get_db
from api.ml import difficulty as diff
from api.ml.features import CEFR_TO_NUM, compute_features, cosine
from api.models import ConversationSession, LearnerProfile, Mistake, Turn, User, Vocab
from api.recs import vocab_to_review
from api.services import llm
from api.services.elevenlabs.speechToText import getTranscript
from api.services.elevenlabs.textToSpeech import createTextToSpeechAudio
from api.services.embeddings import embed

log = logging.getLogger(__name__)
router = APIRouter()



class CreateUser(BaseModel):
    name: str | None = None
    native_lang: str = "en"


class CreateSession(BaseModel):
    user_id: uuid.UUID
    target_lang: str
    level: str | None = None  # e.g. "beginner" / "B1"; omit to keep the learner's current level


class Speak(BaseModel):
    text: str
    speed: float = 1.0
    lang: str | None = None  # target language code, so the voice speaks the right language


@router.post("/tts")
async def speak(body: Speak):
    """Voice any tutor line on demand (replay button, or lines whose audio isn't cached in the browser)."""
    text = body.text.strip()[:1000]
    if not text:
        raise HTTPException(422, "empty text")
    audio = await asyncio.to_thread(createTextToSpeechAudio, text, body.speed, body.lang)
    return {"audio_b64": base64.b64encode(audio).decode(), "audio_mime": "audio/mpeg"}


@router.post("/users")
async def create_user(body: CreateUser, db: AsyncSession = Depends(get_db)):
    user = User(name=body.name, native_lang=body.native_lang)
    db.add(user)
    await db.commit()
    return {"id": str(user.id), "native_lang": user.native_lang}


# ---------- helpers ----------


async def _load(db: AsyncSession, session_id: uuid.UUID):
    session = await db.get(ConversationSession, session_id)
    if not session:
        raise HTTPException(404, "session not found")
    user = await db.get(User, session.user_id)
    profile = await db.scalar(
        select(LearnerProfile).where(
            LearnerProfile.user_id == session.user_id, LearnerProfile.target_lang == session.target_lang
        )
    )
    return session, user, profile


async def _bump_vocab(db: AsyncSession, user_id: uuid.UUID, lang: str, items: list[dict], field: str):
    for it in items:
        lemma = (it.get("lemma") or "").strip().lower()[:100]
        if not lemma:
            continue
        cefr = it.get("cefr") if it.get("cefr") in CEFR_TO_NUM else None
        col = Vocab.__table__.c[field]
        counters = {"times_heard": 0, "times_used": 0, "times_misused": 0}
        counters[field] = 1  # the one being bumped starts at 1 on first insert
        await db.execute(
            pg_insert(Vocab)
            .values(
                user_id=user_id,
                lang=lang,
                lemma=lemma,
                cefr=cefr,
                meaning=it.get("meaning"),
                **counters,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "lang", "lemma"],
                set_={field: col + 1, "last_seen": func.now()},
            )
        )


async def _past_mistakes(db: AsyncSession, user_id: uuid.UUID, lang: str, emb: list[float], k: int = 3) -> list[dict]:
    rows = (
        await db.scalars(
            select(Mistake)
            .where(Mistake.user_id == user_id, Mistake.target_lang == lang, Mistake.embedding.is_not(None))
            .order_by(Mistake.embedding.cosine_distance(emb))
            .limit(k)
        )
    ).all()
    return [{"original": m.original, "corrected": m.corrected, "category": m.category} for m in rows]


async def _tts(text: str, speed: float, lang: str) -> str | None:
    """TTS failure shouldn't lose the turn — the UI falls back to text only."""
    try:
        return base64.b64encode(await asyncio.to_thread(createTextToSpeechAudio, text, speed, lang)).decode()
    except Exception:
        log.exception("TTS failed")
        return None


async def _embed_rows(assistant_turn_id: int, mistake_ids: list[int]):
    """Background: embed the tutor reply and the learner's mistakes (not needed for the response)."""
    try:
        async with dbmod.SessionLocal() as db:
            turn = await db.get(Turn, assistant_turn_id)
            mistakes = [m for m in [await db.get(Mistake, i) for i in mistake_ids] if m]
            texts = [turn.text] + [f"{m.original} → {m.corrected} ({m.category})" for m in mistakes]
            vecs = await embed(texts)
            turn.embedding = vecs[0]
            for m, v in zip(mistakes, vecs[1:]):
                m.embedding = v
            await db.commit()
    except Exception:
        log.exception("background embedding failed")


# ---------- endpoints ----------


@router.post("/sessions")
async def start_session(body: CreateSession, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    profile = await db.scalar(
        select(LearnerProfile).where(
            LearnerProfile.user_id == user.id, LearnerProfile.target_lang == body.target_lang
        )
    )
    chosen = None
    if body.level:
        chosen = diff.level_to_difficulty(body.level)
        if chosen is None:
            raise HTTPException(422, f"unknown level '{body.level}'")
    if not profile:
        # New learner: the level they picked, else config.toml's level, else the built-in default.
        start = chosen or diff.new_learner_difficulty(settings.default_level)
        profile = LearnerProfile(user_id=user.id, target_lang=body.target_lang, difficulty=start, stats={})
        db.add(profile)
    elif chosen is not None:
        # An explicit pick beats the stored level; the controller adapts from there.
        profile.difficulty = chosen
        profile.stats = {k: v for k, v in (profile.stats or {}).items() if k != "smoothed_p"}

    # The learner speaks first: no tutor line is generated here, the first turn comes from POST /turns.
    session = ConversationSession(user_id=user.id, target_lang=body.target_lang, start_difficulty=profile.difficulty)
    db.add(session)
    await db.commit()

    return {
        "session_id": str(session.id),
        "difficulty": {"value": profile.difficulty, "cefr": diff.cefr_label(profile.difficulty)},
    }


@router.post("/sessions/{session_id}/turns")
async def post_turn(
    session_id: uuid.UUID,
    background: BackgroundTasks,
    audio: UploadFile | None = File(None),
    text: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """One conversational exchange. Send `audio` (push-to-talk) or `text` (typing / testing)."""
    session, user, profile = await _load(db, session_id)
    if session.ended_at:
        raise HTTPException(409, "session already ended")

    # 1. Speech → text
    stt_words, audio_s = None, None
    if audio is not None:
        data = await audio.read()
        if not data:
            raise HTTPException(422, "empty audio")
        stt = await asyncio.to_thread(
            getTranscript, (audio.filename or "audio.webm", data, audio.content_type or "audio/webm")
        )
        text, stt_words = stt["text"], stt["words"]
        if stt_words:
            audio_s = stt_words[-1].get("end")
    text = (text or "").strip()
    if not text:
        raise HTTPException(422, "no speech detected")

    # 2. Context: recent history, embedding of this turn, similar past mistakes
    history = list(
        reversed((await db.scalars(select(Turn).where(Turn.session_id == session.id).order_by(Turn.id.desc()).limit(10))).all())
    )
    last_tutor = next((t for t in reversed(history) if t.role == "assistant"), None)
    need_tutor_emb = last_tutor is not None and last_tutor.embedding is None
    vecs = await embed([text] + ([last_tutor.text] if need_tutor_emb else []))
    user_emb = vecs[0]
    tutor_emb = vecs[1] if need_tutor_emb else (last_tutor.embedding if last_tutor else None)
    sim = cosine(user_emb, tutor_emb)
    past = await _past_mistakes(db, user.id, session.target_lang, user_emb)

    # 3. Gemini: reply + analysis of what the learner said
    k = diff.knobs(profile.difficulty)
    turn = await llm.tutor_turn(
        session.target_lang,
        user.native_lang,
        k,
        [{"role": t.role, "text": t.text} for t in history],
        text,
        past,
    )
    analysis = turn.learner_analysis.model_dump()

    # 4. Score the turn and adjust difficulty
    features = compute_features(text, analysis, stt_words, sim)
    perf = diff.performance(features)
    old_d = profile.difficulty
    new_d, smoothed = diff.update(old_d, perf["p"], (profile.stats or {}).get("smoothed_p"))
    profile.difficulty = new_d
    profile.stats = {**(profile.stats or {}), "smoothed_p": smoothed}

    # 5. Persist
    user_turn = Turn(
        session_id=session.id,
        role="user",
        text=text,
        audio_duration_s=audio_s,
        difficulty_at_turn=old_d,
        features={**features, "performance": perf},
        embedding=user_emb,
    )
    db.add(user_turn)
    await db.flush()
    mistakes = [
        Mistake(
            user_id=user.id,
            turn_id=user_turn.id,
            target_lang=session.target_lang,
            category=c["category"],
            original=c["original"],
            corrected=c["corrected"],
            explanation=c["explanation"],
        )
        for c in analysis["corrections"]
    ]
    db.add_all(mistakes)
    tutor_turn = Turn(
        session_id=session.id,
        role="assistant",
        text=turn.reply,
        translation=turn.reply_translation,
        difficulty_at_turn=new_d,
    )
    db.add(tutor_turn)

    lang = session.target_lang
    await _bump_vocab(db, user.id, lang, analysis["vocab_used"], "times_used")
    await _bump_vocab(db, user.id, lang, [v.model_dump() for v in turn.new_vocab_introduced], "times_heard")
    await _bump_vocab(
        db,
        user.id,
        lang,
        [{"lemma": c["corrected"]} for c in analysis["corrections"] if c["category"] == "vocabulary" and len(c["corrected"].split()) == 1],
        "times_misused",
    )
    await db.commit()

    background.add_task(_embed_rows, tutor_turn.id, [m.id for m in mistakes])

    # 6. Voice the reply at a speed matching the new difficulty
    audio_b64 = await _tts(turn.reply, diff.knobs(new_d)["tts_speed"], session.target_lang)

    return {
        "user_turn": {"id": user_turn.id, "text": text, "corrections": analysis["corrections"], "features": features},
        "assistant_turn": {
            "id": tutor_turn.id,
            "text": turn.reply,
            "translation": turn.reply_translation,
            "new_vocab": [v.model_dump() for v in turn.new_vocab_introduced],
        },
        "difficulty": {"before": old_d, "after": new_d, "cefr": diff.cefr_label(new_d), "performance": perf},
        "audio_b64": audio_b64,
        "audio_mime": "audio/mpeg",
    }


async def _build_summary(db: AsyncSession, session: ConversationSession, user: User, profile: LearnerProfile) -> dict:
    turns = (await db.scalars(select(Turn).where(Turn.session_id == session.id).order_by(Turn.id))).all()
    user_turns = [t for t in turns if t.role == "user"]
    mistakes = (
        await db.scalars(select(Mistake).join(Turn, Turn.id == Mistake.turn_id).where(Turn.session_id == session.id))
    ).all()
    categories = Counter(m.category for m in mistakes)
    ps = [t.features["performance"]["p"] for t in user_turns if t.features and "performance" in t.features]
    cl = [t.features["clarity"] for t in user_turns if t.features and t.features.get("clarity") is not None]
    stats = {
        "turns": len(user_turns),
        "words_spoken": sum((t.features or {}).get("word_count", 0) for t in user_turns),
        "avg_performance": round(sum(ps) / len(ps), 3) if ps else None,
        # Average speech-recognizer confidence over spoken turns; None if every turn was typed.
        "avg_clarity": round(sum(cl) / len(cl), 3) if cl else None,
        "difficulty_start": session.start_difficulty,
        "difficulty_end": profile.difficulty,
        "errors_by_category": dict(categories),
        "example_mistakes": [{"original": m.original, "corrected": m.corrected} for m in mistakes[:5]],
    }
    summary = {
        **stats,
        "cefr_end": diff.cefr_label(profile.difficulty),
        "difficulty_trajectory": [round(t.difficulty_at_turn, 2) for t in user_turns] + [profile.difficulty],
        "mistakes": [
            {"original": m.original, "corrected": m.corrected, "explanation": m.explanation, "category": m.category}
            for m in mistakes
        ],
        "vocab_to_review": await vocab_to_review(db, user.id, session.target_lang),
    }
    try:
        summary["coach_note"] = await llm.coach_note(session.target_lang, user.native_lang, stats) if user_turns else None
    except Exception:
        log.exception("coach note failed")
        summary["coach_note"] = None
    return summary


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    session, user, profile = await _load(db, session_id)
    if session.summary is not None:
        return session.summary
    summary = await _build_summary(db, session, user, profile)
    session.summary = summary
    session.end_difficulty = profile.difficulty
    session.ended_at = func.now()
    await db.commit()
    return summary


@router.get("/sessions/{session_id}/summary")
async def get_summary(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    session = await db.get(ConversationSession, session_id)
    if not session:
        raise HTTPException(404, "session not found")
    if session.summary is None:
        raise HTTPException(409, "session not ended yet")
    return session.summary


@router.get("/sessions/{session_id}")
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Used by the UI to restore a conversation after a refresh."""
    session, user, profile = await _load(db, session_id)
    turns = (await db.scalars(select(Turn).where(Turn.session_id == session_id).order_by(Turn.id))).all()
    corrections: dict[int, list] = {}
    for m in (await db.scalars(select(Mistake).join(Turn, Turn.id == Mistake.turn_id).where(Turn.session_id == session_id))).all():
        corrections.setdefault(m.turn_id, []).append(
            {"original": m.original, "corrected": m.corrected, "explanation": m.explanation, "category": m.category}
        )
    return {
        "id": str(session.id),
        "target_lang": session.target_lang,
        "ended": session.ended_at is not None,
        "difficulty": {"value": profile.difficulty, "cefr": diff.cefr_label(profile.difficulty)},
        "turns": [
            {
                "id": t.id,
                "role": t.role,
                "text": t.text,
                "translation": t.translation,
                "corrections": corrections.get(t.id, []),
                "unclear_spans": (t.features or {}).get("unclear_spans", []),
            }
            for t in turns
        ],
    }
