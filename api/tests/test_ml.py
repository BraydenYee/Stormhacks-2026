import numpy as np

from api.ml import difficulty as diff
from api.ml.features import compute_features, cosine, timing_stats
from api.ml.insights import cluster_mistakes, vocab_review_score

CLEAN = {"corrections": [], "on_topic": True, "used_native_language": False, "vocab_used": [{"lemma": "casa", "cefr": "A1"}]}
STRUGGLING = {
    "corrections": [{"category": "grammar"}, {"category": "conjugation"}, {"category": "agreement"}],
    "on_topic": True,
    "used_native_language": True,
    "vocab_used": [],
}


def test_timing_stats():
    words = [
        {"text": "a", "start": 0.0, "end": 0.4, "type": "word"},
        {"text": "b", "start": 0.5, "end": 0.9, "type": "word"},
        {"text": "c", "start": 2.5, "end": 3.0, "type": "word"},  # 1.6s pause
    ]
    s = timing_stats(words)
    assert s["long_pauses"] == 1
    assert s["speaking_rate"] == 1.0


def test_features_error_rate():
    f = compute_features("yo soy ir a la tienda ayer", STRUGGLING)
    assert f["error_count"] == 3 and f["weighted_errors_per_10"] > 3
    assert compute_features("", CLEAN)["word_count"] == 0  # no division by zero


def test_clean_fluent_turn_raises_difficulty():
    f = compute_features("Ayer fui al mercado con mi hermana y compramos muchas frutas", CLEAN, comprehension_sim=0.7)
    p = diff.performance(f)["p"]
    assert p > diff.TARGET_P
    new_d, _ = diff.update(3.0, p)
    assert new_d > 3.0


def test_struggling_turn_lowers_difficulty():
    f = compute_features("yo soy ir tienda", STRUGGLING, comprehension_sim=0.3)
    p = diff.performance(f)["p"]
    assert p < diff.TARGET_P
    new_d, _ = diff.update(3.0, p)
    assert new_d < 3.0


def test_difficulty_stays_in_bounds():
    d, s = 1.0, None
    for _ in range(50):
        d, s = diff.update(d, 0.0, s)
    assert d == diff.D_MIN
    for _ in range(100):
        d, s = diff.update(d, 1.0, s)
    assert d == diff.D_MAX


def test_knobs_scale_with_difficulty():
    easy, hard = diff.knobs(1.0), diff.knobs(6.0)
    assert easy["max_sentence_words"] < hard["max_sentence_words"]
    assert easy["tts_speed"] < hard["tts_speed"]
    assert easy["cefr"] == "A1" and hard["cefr"] == "C2"


def test_cluster_mistakes_separates_groups():
    rng = np.random.default_rng(0)
    a, b = np.zeros(16), np.zeros(16)
    a[0], b[1] = 1, 1
    items = [
        {"embedding": (a + rng.normal(0, 0.05, 16)).tolist(), "category": "grammar", "original": f"a{i}", "corrected": "x"}
        for i in range(6)
    ] + [
        {"embedding": (b + rng.normal(0, 0.05, 16)).tolist(), "category": "vocabulary", "original": f"b{i}", "corrected": "y"}
        for i in range(3)
    ]
    clusters = cluster_mistakes(items, max_clusters=2)
    assert [c["size"] for c in clusters] == [6, 3]
    assert clusters[0]["category"] == "grammar"


def test_vocab_review_ranks_misused_first():
    assert vocab_review_score(5, 4, 3) > vocab_review_score(5, 4, 0)
    assert vocab_review_score(2, 0, 0) > vocab_review_score(5, 4, 0)


def test_cosine_handles_missing():
    assert cosine(None, [1, 0]) is None
    assert cosine([1, 0], [1, 0]) == 1.0
