"""Per-turn learner features. Pure functions — no I/O — so they're easy to test."""

import re

import numpy as np

CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
CEFR_TO_NUM = {lvl: i + 1 for i, lvl in enumerate(CEFR_LEVELS)}

# How much each correction category counts toward the error rate.
ERROR_WEIGHTS = {
    "grammar": 1.0,
    "vocabulary": 0.8,
    "word_order": 0.8,
    "conjugation": 1.0,
    "agreement": 0.7,
    "pronunciation": 0.4,
    "register": 0.3,
    "spelling": 0.2,
    "other": 0.5,
}

LONG_PAUSE_S = 1.0
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def cosine(a: list[float] | np.ndarray | None, b: list[float] | np.ndarray | None) -> float | None:
    if a is None or b is None:
        return None
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return None
    return float(a @ b / (na * nb))


def timing_stats(words: list[dict] | None) -> dict:
    """Speaking rate and pauses from ElevenLabs STT word timings.

    `words` items look like {"text": "hola", "start": 0.12, "end": 0.40, "type": "word"}.
    """
    spoken = [w for w in (words or []) if w.get("type", "word") == "word" and w.get("start") is not None]
    if len(spoken) < 2:
        return {"speaking_rate": None, "long_pauses": 0, "speech_duration_s": None}
    duration = spoken[-1]["end"] - spoken[0]["start"]
    gaps = [b["start"] - a["end"] for a, b in zip(spoken, spoken[1:])]
    return {
        "speaking_rate": round(len(spoken) / duration, 3) if duration > 0 else None,
        "long_pauses": sum(1 for g in gaps if g >= LONG_PAUSE_S),
        "speech_duration_s": round(duration, 2),
    }


def compute_features(
    text: str,
    analysis: dict,
    stt_words: list[dict] | None = None,
    comprehension_sim: float | None = None,
) -> dict:
    """Combine raw text, STT timings and Gemini's analysis into a flat feature dict."""
    tokens = tokenize(text)
    n = len(tokens)
    corrections = analysis.get("corrections") or []
    weighted_errors = sum(ERROR_WEIGHTS.get(c.get("category", "other"), 0.5) for c in corrections)
    vocab_levels = [CEFR_TO_NUM[v["cefr"]] for v in analysis.get("vocab_used") or [] if v.get("cefr") in CEFR_TO_NUM]

    return {
        "word_count": n,
        "type_token_ratio": round(len(set(tokens)) / n, 3) if n else 0.0,
        "error_count": len(corrections),
        "weighted_errors_per_10": round(10 * weighted_errors / max(n, 1), 3),
        "mean_vocab_cefr": round(float(np.mean(vocab_levels)), 2) if vocab_levels else None,
        "used_native_language": bool(analysis.get("used_native_language")),
        "on_topic": bool(analysis.get("on_topic", True)),
        "estimated_cefr": analysis.get("estimated_cefr"),
        "comprehension_sim": round(comprehension_sim, 3) if comprehension_sim is not None else None,
        **timing_stats(stt_words),
    }
