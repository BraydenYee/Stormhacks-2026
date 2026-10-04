# Converse — learn languages by talking

Spoken conversation practice. ElevenLabs does speech-to-text and text-to-speech, Gemini plays the tutor and
analyses each learner turn, and every turn is embedded (pgvector) to drive adaptive difficulty and suggestions.

## Setup

1. **Database** — create a free Postgres on [Neon](https://neon.tech) or [Supabase](https://supabase.com)
   (both ship pgvector). Copy the connection string.
2. **Env** — `cp .env.example .env` and fill in `DATABASE_URL`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`.
   Create `web/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
3. **API** (tables, vector indexes and the topic bank are created on first start):
   ```
   python3 -m venv .venv && .venv/bin/pip install -r api/requirements.txt
   .venv/bin/uvicorn api.main:app --reload
   ```
4. **Web**: `cd web && npm install && npm run dev` → http://localhost:3000

## How it works

- `api/routers/sessions.py` — the turn loop: STT → embed → retrieve similar past mistakes → Gemini
  (structured JSON: reply + learner analysis) → score + adjust difficulty → persist → TTS.
- `api/ml/difficulty.py` — proportional controller keeping performance near 75%; difficulty (1–6 ≈ A1–C2)
  sets the tutor's vocabulary, sentence length and TTS speed.
- `api/ml/insights.py` — KMeans over mistake embeddings for weak spots; vocab review scoring.
- `api/recs.py` — topic recommendations by nearest-neighbour on the learner's engaged turns.
- `web/` — Next.js 16 app: landing, push-to-talk session page, progress dashboard.

Unit tests for the scoring/clustering logic: `.venv/bin/python -m pytest api/tests`.
