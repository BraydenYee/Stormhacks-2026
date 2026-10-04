import numpy as np

from api.ml import difficulty as diff
import math

from api.ml.features import add_off_topic_mistake, compute_features, confidence_stats, cosine, timing_stats
from api.services import llm
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


def _word(text, prob):
    return {"text": text, "type": "word", "start": 0.0, "end": 0.3, "logprob": math.log(prob)}


def test_confidence_stats_marks_unclear_words_by_position():
    text = "yo quiero una casa"
    words = [_word("yo", 0.95), _word("quiero", 0.3), _word("una", 0.9), _word("casa", 0.4)]
    s = confidence_stats(words, text)
    assert s["unclear_count"] == 2
    assert [text[a:b] for a, b in s["unclear_spans"]] == ["quiero", "casa"]
    assert s["min_word_confidence"] == 0.3
    assert 0.5 < s["clarity"] < 0.7


def test_confidence_stats_handles_text_input_and_repeated_words():
    assert confidence_stats(None, "typed")["clarity"] is None
    # the same word twice: spans must point at each occurrence, not the first one twice
    s = confidence_stats([_word("no", 0.9), _word("no", 0.2)], "no no")
    assert s["unclear_spans"] == [[3, 5]]


def test_clear_speech_scores_higher_than_unclear_and_typed_turns_are_not_penalised():
    base = compute_features("Ayer fui al mercado con mi hermana y compramos muchas frutas frescas para la cena", CLEAN, comprehension_sim=0.7)
    clear = {**base, "clarity": 0.95}
    unclear = {**base, "clarity": 0.45}
    assert diff.performance(clear)["p"] > diff.performance(unclear)["p"]
    typed = diff.performance({**base, "clarity": None})
    assert typed["pronunciation"] is None and typed["p"] > 0.99


def test_cosine_handles_missing():
    assert cosine(None, [1, 0]) is None
    assert cosine([1, 0], [1, 0]) == 1.0


# ---------- stricter scoring ----------

LONG = "Ayer fui al mercado con mi hermana y compramos muchas frutas frescas para la cena"


def test_one_error_in_a_short_turn_costs_a_lot():
    one_error = {**CLEAN, "corrections": [{"category": "grammar"}]}
    f = compute_features("Yo ir al mercado ayer con mi hermana", one_error, comprehension_sim=0.7)
    assert diff.performance(f)["accuracy"] < 0.4
    assert diff.performance(f)["p"] < diff.TARGET_P


def test_short_clean_turn_is_not_full_marks():
    f = compute_features("Hola, estoy bien", CLEAN, comprehension_sim=0.7)
    assert diff.performance(f)["p"] < 0.9


def test_off_topic_turn_scores_zero_comprehension_and_low_overall():
    f = compute_features(LONG, {**CLEAN, "on_topic": False, "off_topic_reason": "Did not answer"}, comprehension_sim=0.7)
    perf = diff.performance(f)
    assert perf["comprehension"] == 0.0
    on_topic = diff.performance(compute_features(LONG, CLEAN, comprehension_sim=0.7))
    assert perf["p"] < on_topic["p"] - 0.1


def test_clarity_comes_from_recognizer_word_confidence_and_typed_turns_have_none():
    words = [
        {"text": "hola", "start": 0, "end": 0.4, "type": "word", "logprob": -0.02},
        {"text": "casa", "start": 0.5, "end": 0.9, "type": "word", "logprob": -2.0},
    ]
    f = compute_features("hola casa", CLEAN, stt_words=words)
    assert f["unclear_count"] == 1 and f["clarity"] < 0.6
    assert compute_features("hola casa", CLEAN)["clarity"] is None


def test_off_topic_reason_is_only_kept_when_off_topic():
    off = compute_features(LONG, {**CLEAN, "on_topic": False, "off_topic_reason": "why"})
    on = compute_features(LONG, {**CLEAN, "on_topic": True, "off_topic_reason": "stale"})
    assert off["on_topic"] is False and off["off_topic_reason"] == "why"
    assert on["off_topic_reason"] is None


# ---------- prompts ----------


def test_system_prompt_asks_for_thorough_errors_and_off_topic_check():
    k = diff.knobs(3.0)
    p = llm.system_prompt("es", "en", k, [])
    assert "EVERY error" in p and "on_topic" in p
    assert "dim sum" not in p.lower()


def test_tutor_turn_sends_previous_message_and_unclear_word_hints(monkeypatch):
    import asyncio

    seen = {}

    async def fake_structured(model_cls, system, contents, temperature=0.7):
        seen["system"], seen["contents"] = system, contents
        return "ok"

    monkeypatch.setattr(llm, "_structured", fake_structured)
    hist = [{"role": "assistant", "text": "What is your favorite food?"}]
    asyncio.run(llm.tutor_turn("es", "en", diff.knobs(3.0), hist, "me gusta", [], ["gusta"]))
    assert "What is your favorite food?" in seen["system"]
    assert "gusta" in seen["system"] and "speech recognizer was unsure" in seen["system"]
    assert len(seen["contents"][-1].parts) == 1  # text only: no audio goes to Gemini

    asyncio.run(llm.tutor_turn("es", "en", diff.knobs(3.0), hist, "me gusta", []))
    assert "speech recognizer was unsure" not in seen["system"]


# ---------- intended vs estimated accuracy score ----------

# (label, number of errors, category, text, intended accuracy range)
SCORE_CASES = [
    ("clean, 14 words", 0, None, LONG, (0.9, 1.0)),
    ("one spelling slip, 14 words", 1, "spelling", LONG, (0.8, 1.0)),
    ("one grammar error, 14 words", 1, "grammar", LONG, (0.4, 0.7)),
    ("one grammar error, 7 words", 1, "grammar", "Yo ir al mercado ayer con mi hermana", (0.0, 0.3)),
    ("three errors, 12 words", 3, "grammar", "Yo es muy gustar los arroz fritos y yo comer ayer", (0.0, 0.1)),
]


def test_estimated_accuracy_matches_intended_ranges(report):
    rows, hits = [], 0
    for label, n, cat, text, (lo, hi) in SCORE_CASES:
        analysis = {**CLEAN, "corrections": [{"category": cat}] * n}
        perf = diff.performance(compute_features(text, analysis, comprehension_sim=0.7))
        ok = lo <= perf["accuracy"] <= hi
        hits += ok
        rows.append(f"  {'PASS' if ok else 'FAIL'}  {label:<30} intended {lo:.1f}-{hi:.1f}   estimated {perf['accuracy']:.2f}   (turn score {perf['p']:.2f})")
    report(f"Accuracy score: intended vs estimated ({hits}/{len(SCORE_CASES)} in range)", rows)
    assert hits == len(SCORE_CASES)


def test_reply_that_missed_the_question_counts_as_a_mistake():
    off = {**CLEAN, "on_topic": False, "off_topic_reason": "Asked about food, replied about the cinema",
           "previous_tutor_question": "your favorite dish"}
    a = add_off_topic_mistake(off, "Ayer fui al cine")
    (m,) = a["corrections"]
    assert m["category"] == "off_topic" and m["original"] == "Ayer fui al cine"
    assert "your favorite dish" in m["corrected"] and m["explanation"].startswith("Asked about food")
    f = compute_features(LONG, a, comprehension_sim=0.7)
    assert f["error_count"] == 1 and f["weighted_errors_per_10"] > 0
    assert diff.performance(f)["accuracy"] < 1.0


def test_on_topic_reply_is_left_alone():
    assert add_off_topic_mistake(CLEAN, "hola") is CLEAN


def test_difficulty_drops_quickly_when_learner_is_not_showing_proficiency(report):
    f = compute_features("yo soy ir tienda", STRUGGLING, comprehension_sim=0.3)
    p = diff.performance(f)["p"]
    d, s, path = 4.0, None, [4.0]
    for _ in range(3):
        d, s = diff.update(d, p, s, "A2")
        path.append(d)
    report("Difficulty after repeated struggling turns (start B2, Gemini estimates A2)", ["  " + " -> ".join(f"{x:.2f}" for x in path)])
    assert path[1] <= 3.4 and path[3] <= 2.4  # at least 0.6 down after one turn, 1.6 after three


def test_estimated_level_below_current_pulls_difficulty_down_but_never_up():
    mid = diff.TARGET_P
    assert diff.update(4.0, mid, None, "A2")[0] < diff.update(4.0, mid, None, None)[0]
    assert diff.update(2.0, mid, None, "C2")[0] == diff.update(2.0, mid, None, None)[0]
    assert diff.update(3.0, mid, None, "garbage")[0] == diff.update(3.0, mid, None, None)[0]
