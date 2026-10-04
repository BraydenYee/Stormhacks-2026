"""Queries shared by the session summary and the analytics dashboard."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.ml.insights import interest_centroid, vocab_review_score
from api.models import ConversationSession, Topic, Turn, Vocab


async def vocab_to_review(db: AsyncSession, user_id: uuid.UUID, lang: str, limit: int = 8) -> list[dict]:
    rows = (await db.scalars(select(Vocab).where(Vocab.user_id == user_id, Vocab.lang == lang))).all()
    scored = [
        (vocab_review_score(v.times_heard, v.times_used, v.times_misused), v)
        for v in rows
        if v.times_misused > 0 or (v.times_heard > 0 and v.times_used == 0)
    ]
    scored.sort(key=lambda s: -s[0])
    return [
        {
            "lemma": v.lemma,
            "cefr": v.cefr,
            "meaning": v.meaning,
            "times_heard": v.times_heard,
            "times_used": v.times_used,
            "times_misused": v.times_misused,
            "score": score,
        }
        for score, v in scored[:limit]
    ]


async def recommend_topics(
    db: AsyncSession, user_id: uuid.UUID, lang: str, difficulty: float, limit: int = 3
) -> list[dict]:
    """Topics near what the learner engages with, within reach of their level, not yet done."""
    done = set(
        await db.scalars(
            select(ConversationSession.topic).where(
                ConversationSession.user_id == user_id, ConversationSession.target_lang == lang
            )
        )
    )

    user_turns = (
        await db.execute(
            select(Turn.embedding, Turn.features)
            .join(ConversationSession, ConversationSession.id == Turn.session_id)
            .where(
                ConversationSession.user_id == user_id,
                ConversationSession.target_lang == lang,
                Turn.role == "user",
                Turn.embedding.is_not(None),
            )
            .order_by(Turn.id.desc())
            .limit(200)
        )
    ).all()
    centroid = interest_centroid(
        [{"embedding": e, "word_count": (f or {}).get("word_count", 0)} for e, f in user_turns]
    )

    # Allow topics up to one level above the learner: a stretch, not a wall.
    q = select(Topic).where(Topic.cefr_min <= difficulty + 1.0, Topic.embedding.is_not(None))
    if done:
        q = q.where(Topic.title.not_in(done))
    q = q.order_by(Topic.embedding.cosine_distance(centroid)) if centroid else q.order_by(Topic.cefr_min.desc())
    topics = (await db.scalars(q.limit(limit))).all()
    return [{"id": t.id, "title": t.title, "description": t.description, "cefr_min": t.cefr_min} for t in topics]
