"""Queries shared by the session summary and the analytics dashboard."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.ml.insights import vocab_review_score
from api.models import Vocab


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
