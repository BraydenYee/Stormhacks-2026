"""Gemini: the conversation partner, learner-turn analysis, and small labeling jobs."""

import asyncio
import logging
from functools import lru_cache

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field

from api.config import settings

log = logging.getLogger(__name__)

LANGUAGES = {
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Mandarin Chinese",
    "en": "English",
}

CATEGORIES = "grammar, conjugation, agreement, word_order, vocabulary, pronunciation, register, spelling, other"


@lru_cache
def client() -> genai.Client:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=settings.gemini_api_key)


# ---------- structured output schemas ----------


class Correction(BaseModel):
    original: str = Field(description="The learner's erroneous fragment, verbatim")
    corrected: str = Field(description="The corrected fragment")
    explanation: str = Field(description="One short sentence, in the learner's native language")
    category: str = Field(description=f"One of: {CATEGORIES}")


class VocabItem(BaseModel):
    lemma: str = Field(description="Dictionary form in the target language")
    cefr: str = Field(description="A1, A2, B1, B2, C1 or C2")


class NewVocab(VocabItem):
    meaning: str = Field(description="Short gloss in the learner's native language")


class LearnerAnalysis(BaseModel):
    corrections: list[Correction]
    on_topic: bool = Field(description="Did the learner respond meaningfully to what the tutor said?")
    used_native_language: bool = Field(description="Did the learner fall back to their native language for a substantial part?")
    vocab_used: list[VocabItem] = Field(description="Content words the learner used correctly (max 8)")
    estimated_cefr: str = Field(description="Your estimate of the learner's level from this turn: A1–C2")


class TutorTurn(BaseModel):
    learner_analysis: LearnerAnalysis
    reply: str = Field(description="Your spoken reply in the target language")
    reply_translation: str = Field(description="Translation of reply into the learner's native language")
    new_vocab_introduced: list[NewVocab] = Field(description="Words in your reply likely new at this level (max 3)")


class Opener(BaseModel):
    reply: str
    reply_translation: str
    new_vocab_introduced: list[NewVocab]


# ---------- prompts ----------


def system_prompt(target: str, native: str, topic: str, k: dict, past_mistakes: list[dict]) -> str:
    lines = [
        f"You are a warm, curious conversation partner helping someone practice {LANGUAGES.get(target, target)}.",
        f"The learner's native language is {LANGUAGES.get(native, native)}. Today's topic: {topic}.",
        "Your job is to keep a natural spoken conversation going — conversation is how they learn.",
        "",
        f"Speak at CEFR level {k['cefr']}:",
        f"- At most {k['max_sentences']} sentences, each at most {k['max_sentence_words']} words.",
        f"- Use vocabulary appropriate for {k['cefr']}; {'idioms are welcome' if k['idioms'] else 'avoid idioms and slang'}.",
        f"- Native-language glosses in parentheses: {k['native_gloss']}.",
        f"- Corrections: {k['correction_style']}. A recast means naturally repeating their idea correctly in your reply.",
        "- Always end with a question or prompt that invites them to keep talking.",
        "- Your reply will be read aloud by TTS: no markdown, emoji or lists.",
    ]
    if past_mistakes:
        lines += ["", "This learner has made similar mistakes before. If natural, create an opportunity to practice:"]
        lines += [f"- '{m['original']}' → '{m['corrected']}' ({m['category']})" for m in past_mistakes]
    lines += [
        "",
        "Also analyze the learner's latest message precisely. Only list real errors; "
        "don't 'correct' acceptable variants. Transcripts come from speech recognition, so ignore "
        "punctuation and capitalization, and only mark pronunciation when the transcript makes it evident.",
    ]
    return "\n".join(lines)


def _history_contents(history: list[dict]) -> list[types.Content]:
    return [
        types.Content(role="model" if h["role"] == "assistant" else "user", parts=[types.Part(text=h["text"])])
        for h in history
    ]


RETRYABLE_CODES = {429, 500, 503, 504}


async def _structured(model_cls: type[BaseModel], system: str, contents, temperature: float = 0.7):
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=model_cls,
        temperature=temperature,
        # Latency matters more than deep reasoning for a live conversation.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    # Overload (503) is usually brief: retry the primary model with backoff, then try the fallback once.
    attempts = [(settings.gemini_model, d) for d in (0.0, 1.0, 2.0, 4.0)]
    if settings.gemini_fallback_model and settings.gemini_fallback_model != settings.gemini_model:
        attempts.append((settings.gemini_fallback_model, 0.0))

    for model, delay in attempts:
        if delay:
            await asyncio.sleep(delay)
        try:
            resp = await client().aio.models.generate_content(model=model, contents=contents, config=config)
            break
        except genai_errors.APIError as e:
            if e.code not in RETRYABLE_CODES:
                raise
            log.warning("Gemini %s returned %s, retrying", model, e.code)
            last_error = e
    else:
        raise last_error
    if resp.parsed is None:
        return model_cls.model_validate_json(resp.text)
    return resp.parsed


async def tutor_turn(
    target: str, native: str, topic: str, k: dict, history: list[dict], learner_text: str, past_mistakes: list[dict]
) -> TutorTurn:
    contents = _history_contents(history) + [types.Content(role="user", parts=[types.Part(text=learner_text)])]
    return await _structured(TutorTurn, system_prompt(target, native, topic, k, past_mistakes), contents)


async def opener(target: str, native: str, topic: str, k: dict) -> Opener:
    system = system_prompt(target, native, topic, k, [])
    msg = "Start the conversation: greet the learner briefly and ask an easy, open question about the topic."
    return await _structured(Opener, system, msg)


class _Labels(BaseModel):
    labels: list[str]


async def label_clusters(clusters: list[dict], target: str, native: str) -> list[str]:
    """Give each weak-spot cluster a short human-readable name like 'ser vs. estar'."""
    if not clusters:
        return []
    blocks = []
    for i, c in enumerate(clusters):
        ex = "; ".join(f"{e['original']} → {e['corrected']}" for e in c["examples"])
        blocks.append(f"{i + 1}. ({c['category']}) {ex}")
    system = (
        f"You label groups of {LANGUAGES.get(target, target)} learner mistakes. For each numbered group, "
        f"return a 2–6 word label in {LANGUAGES.get(native, native)} naming the underlying concept. "
        "Return exactly one label per group, in order."
    )
    out = await _structured(_Labels, system, "\n".join(blocks), temperature=0.2)
    labels = out.labels + [c["category"] for c in clusters[len(out.labels) :]]
    return labels[: len(clusters)]


class _CoachNote(BaseModel):
    note: str


async def coach_note(target: str, native: str, stats: dict) -> str:
    system = (
        f"You are a {LANGUAGES.get(target, target)} tutor writing a 2–3 sentence encouraging end-of-session note "
        f"in {LANGUAGES.get(native, native)}. Mention one concrete strength and one concrete thing to focus on next. "
        "Base it strictly on the stats given."
    )
    return (await _structured(_CoachNote, system, str(stats), temperature=0.5)).note
