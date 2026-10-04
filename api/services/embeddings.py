import numpy as np
from google.genai import types

from api.config import settings
from api.services.llm import client


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed texts with Gemini, L2-normalized (required when truncating dimensions)."""
    if not texts:
        return []
    resp = await client().aio.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=settings.embedding_dim,
        ),
    )
    out = []
    for e in resp.embeddings:
        v = np.asarray(e.values, dtype=float)
        n = np.linalg.norm(v)
        out.append((v / n if n else v).tolist())
    return out


async def embed_one(text: str) -> list[float]:
    return (await embed([text]))[0]
