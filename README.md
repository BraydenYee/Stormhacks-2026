# Converse — learn languages by talking

Spoken conversation practice. ElevenLabs does speech-to-text and text-to-speech, Gemini plays the tutor and
analyses each learner turn, and every turn is embedded (pgvector) to drive adaptive difficulty and suggestions.

## Setup

1. **Database** — create a free Postgres on [Neon](https://neon.tech) or [Supabase](https://supabase.com)
   (both ship pgvector). Copy the connection string.
2. **Env** — `cp .env.example .env` and fill in `DATABASE_URL`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`.
   Create `web/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
3. **API** (tables and vector indexes are created on first start):
   ```
   python3 -m venv .venv && .venv/bin/pip install -r api/requirements.txt
   .venv/bin/uvicorn api.main:app --reload
   ```
4. **Web**: `cd web && npm install && npm run dev` → http://localhost:3000

## Voice, prompt and config modules

| File | Used for | Run on its own |
|---|---|---|
| `api/services/Elevenlabs/speechToText.py` | `getTranscript()` turns the browser's recording into text plus word timings | `python -m api.services.Elevenlabs.speechToText` |
| `api/services/Elevenlabs/textToSpeech.py` | `createTextToSpeechAudio()` voices every tutor reply (voice ID, voice settings, model all set here) | `python -m api.services.Elevenlabs.textToSpeech` |
| `api/services/gemini_chat.py` | `build_system_instruction()` opens the tutor prompt; `generation_config()` and `load_config()` are shared | `python -m api.services.gemini_chat` |
| `config.toml` | `model`, `language` (landing-page default), `level` (where new learners start) | – |

Run the commands from the project root. Restart the API after editing any of these. A `GEMINI_MODEL` env var
overrides `config.toml`'s `model`. See what the server resolved: http://localhost:8000/config

The app's own tutor logic (`llm.py`: structured replies, corrections, history) builds on `gemini_chat.py`
rather than repeating it. API keys come only from `.env`.

## How it works

- `api/routers/sessions.py` — the turn loop: STT → embed → retrieve similar past mistakes → Gemini
  (structured JSON: reply + learner analysis) → score + adjust difficulty → persist → TTS.
- `api/ml/difficulty.py` — proportional controller keeping performance near 75%; difficulty (1–6 ≈ A1–C2)
  sets the tutor's vocabulary, sentence length and TTS speed.
- `api/ml/insights.py` — KMeans over mistake embeddings for weak spots; vocab review scoring.
- `api/recs.py` — which words to review, scored from how often each was heard, used and misused.
- `web/` — Next.js 16 app: landing, push-to-talk session page, progress dashboard.

Unit tests for the scoring/clustering logic: `.venv/bin/python -m pytest api/tests`.
