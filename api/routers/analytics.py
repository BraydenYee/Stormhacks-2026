import logging
import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.ml import difficulty as diff
from api.ml.insights import cluster_mistakes
from api.models import ConversationSession, LearnerProfile, Mistake, Turn, User
from api.recs import recommend_topics, vocab_to_review
from api.services import llm

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users/{user_id}/analytics")
async def analytics(user_id: uuid.UUID, lang: str | None = None, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "user not found")

    if lang is None:
        lang = await db.scalar(
            select(ConversationSession.target_lang)
            .where(ConversationSession.user_id == user_id)
            .order_by(ConversationSession.created_at.desc())
            .limit(1)
        )
    profile = (
        await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id, LearnerProfile.target_lang == lang))
        if lang
        else None
    )
    if not profile:
        return {"lang": lang, "empty": True}

    sessions = (
        await db.scalars(
            select(ConversationSession)
            .where(ConversationSession.user_id == user_id, ConversationSession.target_lang == lang)
            .order_by(ConversationSession.created_at)
        )
    ).all()

    # Errors per session, per category
    rows = (
        await db.execute(
            select(Turn.session_id, Mistake.category)
            .join(Turn, Turn.id == Mistake.turn_id)
            .where(Mistake.user_id == user_id, Mistake.target_lang == lang)
        )
    ).all()
    per_session: dict[uuid.UUID, Counter] = {}
    for sid, cat in rows:
        per_session.setdefault(sid, Counter())[cat] += 1

    # Weak spots: cluster mistake embeddings, then name each cluster
    mistakes = (
        await db.scalars(
            select(Mistake)
            .where(Mistake.user_id == user_id, Mistake.target_lang == lang, Mistake.embedding.is_not(None))
            .order_by(Mistake.id.desc())
            .limit(300)
        )
    ).all()
    clusters = cluster_mistakes(
        [{"embedding": m.embedding, "category": m.category, "original": m.original, "corrected": m.corrected} for m in mistakes]
    )
    try:
        labels = await llm.label_clusters(clusters, lang, user.native_lang)
    except Exception:
        log.exception("cluster labeling failed")
        labels = [c["category"] for c in clusters]
    for c, label in zip(clusters, labels):
        c["label"] = label

    turn_count = len(
        (
            await db.scalars(
                select(Turn.id)
                .join(ConversationSession, ConversationSession.id == Turn.session_id)
                .where(ConversationSession.user_id == user_id, ConversationSession.target_lang == lang, Turn.role == "user")
            )
        ).all()
    )

    return {
        "lang": lang,
        "empty": False,
        "difficulty": {"value": profile.difficulty, "cefr": diff.cefr_label(profile.difficulty)},
        "totals": {"sessions": len(sessions), "turns": turn_count, "mistakes": sum(sum(c.values()) for c in per_session.values())},
        "sessions": [
            {
                "id": str(s.id),
                "topic": s.topic,
                "date": s.created_at.isoformat(),
                "difficulty_start": s.start_difficulty,
                "difficulty_end": s.end_difficulty if s.end_difficulty is not None else profile.difficulty,
                "errors": dict(per_session.get(s.id, {})),
                "ended": s.ended_at is not None,
            }
            for s in sessions
        ],
        "weak_spots": clusters,
        "vocab_to_review": await vocab_to_review(db, user_id, lang, limit=10),
        "recommended_topics": await recommend_topics(db, user_id, lang, profile.difficulty),
    }
