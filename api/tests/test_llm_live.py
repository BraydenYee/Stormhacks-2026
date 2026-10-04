"""Hits the real Gemini API, so it is skipped unless RUN_LIVE_LLM=1. Model output varies, so assertions are loose."""

import asyncio
import os

import pytest

from api.ml import difficulty as diff
from api.services import llm

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_LLM") != "1", reason="set RUN_LIVE_LLM=1 to call Gemini")

HIST = [
    {"role": "user", "text": "Me gusta la comida china."},
    {"role": "assistant", "text": "¡Qué bien! A mí también me gusta. ¿Cuál es tu plato favorito?"},
]


@pytest.fixture(autouse=True)
def fresh_client():
    # Each test runs its own event loop, and the cached client binds to the first one it sees.
    llm.client.cache_clear()


def _analyse(text: str):
    return asyncio.run(llm.tutor_turn("es", "en", diff.knobs(3.0), HIST, text, [])).learner_analysis


def test_unrelated_reply_is_flagged_off_topic_with_a_reason():
    a = _analyse("Ayer fui al cine con mi hermano.")
    assert a.on_topic is False and a.off_topic_reason


def test_fitting_reply_is_not_flagged():
    a = _analyse("Mi plato favorito es el arroz frito.")
    assert a.on_topic is True and a.off_topic_reason is None


def test_every_error_in_a_multi_error_sentence_is_listed():
    a = _analyse("Yo es muy gustar los arroz fritos y yo comer ayer en restaurante bueno.")
    assert len(a.corrections) >= 3


# (reply, intended on_topic, intended minimum number of errors; 0 means the sentence is correct)
EVAL_CASES = [
    ("Mi plato favorito es el arroz frito.", True, 0),
    ("Me encanta la sopa de wonton, sobre todo con mucho caldo.", True, 0),
    ("Ayer fui al cine con mi hermano.", False, 0),
    ("Me gustan mucho los arándanos.", False, 0),
    ("Mi plato favorito es el arroz frito pero yo no gusta el pescado.", True, 1),
    ("Yo es muy gustar los arroz fritos y yo comer ayer en restaurante bueno.", True, 3),
    ("Yo tiene hambre y quiero comer los pollo.", True, 2),
    ("Mañana voy a la playa con mis amigos.", False, 0),
]


def test_estimated_vs_intended_flags(report):
    llm.client.cache_clear()

    async def run_all():
        return await asyncio.gather(*[
            llm.tutor_turn("es", "en", diff.knobs(3.0), HIST, reply, []) for reply, _, _ in EVAL_CASES
        ])

    results = asyncio.run(run_all())
    rows, topic_hits, found, expected, false_alarms, clean = [], 0, 0, 0, 0, 0
    for (reply, want_topic, want_errors), turn in zip(EVAL_CASES, results):
        a = turn.learner_analysis
        got_errors = len(a.corrections)
        topic_ok = a.on_topic == want_topic
        topic_hits += topic_ok
        if want_errors:
            found += min(got_errors, want_errors)
            expected += want_errors
        else:
            clean += 1
            false_alarms += got_errors > 0
        rows.append(
            f"  {'PASS' if topic_ok else 'FAIL'}  on_topic intended {str(want_topic):<5} estimated {str(a.on_topic):<5} | "
            f"errors intended >={want_errors} estimated {got_errors} | {reply[:44]}"
        )
    n = len(EVAL_CASES)
    rows += [
        "",
        f"  Off-topic detection accuracy: {topic_hits}/{n} = {100 * topic_hits / n:.0f}%",
        f"  Mistake recall:               {found}/{expected} = {100 * found / max(expected, 1):.0f}%",
        f"  False alarms on clean replies:{false_alarms:>3}/{clean}",
    ]
    report("Gemini analysis: intended vs estimated", rows)
    assert topic_hits / n >= 0.75
    assert found / max(expected, 1) >= 0.6
