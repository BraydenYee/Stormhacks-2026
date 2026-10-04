"""Adaptive difficulty controller.

Difficulty `d` is a continuous score in [1, 6] mapped onto CEFR A1–C2. After each learner
turn we score their performance `p` in [0, 1] and nudge `d` toward keeping them in the
"stretched but succeeding" zone (target p ≈ 0.75). Gains are asymmetric: we back off
faster when someone struggles than we ramp up when they're comfortable.
"""

from api.ml.features import CEFR_LEVELS

D_MIN, D_MAX = 1.0, 6.0
TARGET_P = 0.75
GAIN_UP = 0.8
GAIN_DOWN = 0.5
EMA_ALPHA = 0.6  # weight of the newest turn in the smoothed performance


# Names a person might type in config.toml or pick in the UI → starting difficulty (1–6 ≈ A1–C2).
LEVEL_NAMES = {
    "beginner": 1.5,
    "elementary": 2.0,
    "intermediate": 3.0,
    "upper-intermediate": 4.0,
    "advanced": 5.0,
    "native": 6.0,
    "a1": 1.0,
    "a2": 2.0,
    "b1": 3.0,
    "b2": 4.0,
    "c1": 5.0,
    "c2": 6.0,
}


def level_to_difficulty(level: str | None) -> float | None:
    """'beginner' / 'B1' / 'upper intermediate' → difficulty, or None if unrecognised."""
    if not level:
        return None
    return LEVEL_NAMES.get(level.strip().lower().replace(" ", "-"))


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def performance(f: dict) -> dict:
    """Score one learner turn. Returns the components too, for display/debugging."""
    accuracy = 1.0 - clamp(f.get("weighted_errors_per_10", 0.0) / 3.0)

    length = clamp(f.get("word_count", 0) / 8.0)
    rate = f.get("speaking_rate")
    fluency = length if rate is None else 0.5 * length + 0.5 * clamp(rate / 2.0)
    fluency = clamp(fluency - 0.1 * f.get("long_pauses", 0))

    sim = f.get("comprehension_sim")
    if not f.get("on_topic", True):
        comprehension = 0.2
    elif sim is None:
        comprehension = 1.0
    else:
        # Embedding similarity between tutor question and learner reply; ~0.3 is unrelated, ~0.7 clearly related.
        comprehension = clamp((sim - 0.3) / 0.4)

    target_lang_use = 0.0 if f.get("used_native_language") else 1.0

    p = 0.4 * accuracy + 0.25 * fluency + 0.25 * comprehension + 0.1 * target_lang_use
    return {
        "p": round(p, 3),
        "accuracy": round(accuracy, 3),
        "fluency": round(fluency, 3),
        "comprehension": round(comprehension, 3),
        "target_lang_use": target_lang_use,
    }


def update(d: float, p: float, prev_smoothed: float | None = None) -> tuple[float, float]:
    """Return (new_difficulty, smoothed_performance)."""
    smoothed = p if prev_smoothed is None else EMA_ALPHA * p + (1 - EMA_ALPHA) * prev_smoothed
    err = smoothed - TARGET_P
    gain = GAIN_UP if err > 0 else GAIN_DOWN
    return round(clamp(d + gain * err, D_MIN, D_MAX), 3), round(smoothed, 3)


def cefr_label(d: float) -> str:
    return CEFR_LEVELS[int(clamp(round(d), D_MIN, D_MAX)) - 1]


def knobs(d: float) -> dict:
    """Translate difficulty into concrete instructions for the tutor and the TTS voice."""
    t = (clamp(d, D_MIN, D_MAX) - D_MIN) / (D_MAX - D_MIN)  # 0..1
    return {
        "cefr": cefr_label(d),
        "max_sentence_words": int(round(6 + t * 19)),  # 6 → 25
        "max_sentences": 2 if d < 3 else 3,
        "idioms": d >= 4,
        "native_gloss": "often" if d < 2 else "for new or tricky words" if d < 3.5 else "never",
        "correction_style": "gentle recast only" if d < 3 else "recast, plus a brief note on recurring errors",
        "tts_speed": round(0.8 + t * 0.25, 2),  # ElevenLabs allows 0.7–1.2
    }
