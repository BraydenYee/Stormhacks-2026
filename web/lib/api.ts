const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Correction = { original: string; corrected: string; explanation: string; category: string };
export type Vocab = { lemma: string; cefr: string | null; meaning?: string | null };
export type Difficulty = { value: number; cefr: string };

export type TurnResult = {
  user_turn: { id: number; text: string; corrections: Correction[] };
  assistant_turn: { id: number; text: string; translation: string | null; new_vocab: Vocab[] };
  difficulty: { before: number; after: number; cefr: string; performance: { p: number } };
  audio_b64: string | null;
  audio_mime: string;
};

export type StartResult = {
  session_id: string;
  topic: string;
  difficulty: Difficulty;
  assistant_turn: TurnResult["assistant_turn"];
  audio_b64: string | null;
  audio_mime: string;
};

export type SessionState = {
  id: string;
  topic: string;
  target_lang: string;
  ended: boolean;
  difficulty: Difficulty;
  turns: { id: number; role: "user" | "assistant"; text: string; translation: string | null; corrections: Correction[] }[];
};

/** What the shared config.toml / ElevenLabs settings currently resolve to on the server. */
export type AppConfig = {
  language: string | null;
  language_name: string;
  level: string | null;
  gemini_model: string;
  elevenlabs: { voice_id: string; stt_model: string; tts_model: string };
};

export type Topic = { id: number; title: string; description: string; cefr_min: number };

export type Summary = {
  turns: number;
  words_spoken: number;
  avg_performance: number | null;
  difficulty_start: number;
  difficulty_end: number;
  cefr_end: string;
  difficulty_trajectory: number[];
  errors_by_category: Record<string, number>;
  mistakes: Correction[];
  vocab_to_review: (Vocab & { times_misused: number })[];
  suggested_topics: Topic[];
  coach_note: string | null;
};

export type Analytics =
  | { empty: true; lang: string | null }
  | {
      empty: false;
      lang: string;
      difficulty: Difficulty;
      totals: { sessions: number; turns: number; mistakes: number };
      sessions: {
        id: string;
        topic: string;
        date: string;
        difficulty_start: number;
        difficulty_end: number;
        errors: Record<string, number>;
        ended: boolean;
      }[];
      weak_spots: { label: string; size: number; category: string; examples: { original: string; corrected: string }[] }[];
      vocab_to_review: (Vocab & { times_misused: number; times_heard: number; times_used: number })[];
      recommended_topics: Topic[];
    };

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  createUser: (native_lang: string) => req<{ id: string }>("/users", json({ native_lang })),
  config: () => req<AppConfig>("/config"),
  startSession: (user_id: string, target_lang: string, topic?: string, level?: string) =>
    req<StartResult>("/sessions", json({ user_id, target_lang, topic, level })),
  getSession: (id: string) => req<SessionState>(`/sessions/${id}`),
  sendAudio: (id: string, blob: Blob) => {
    const fd = new FormData();
    fd.append("audio", blob, "speech.webm");
    return req<TurnResult>(`/sessions/${id}/turns`, { method: "POST", body: fd });
  },
  sendText: (id: string, text: string) => {
    const fd = new FormData();
    fd.append("text", text);
    return req<TurnResult>(`/sessions/${id}/turns`, { method: "POST", body: fd });
  },
  speak: (text: string, speed = 1) =>
    req<{ audio_b64: string; audio_mime: string }>("/tts", json({ text, speed })),
  endSession: (id: string) => req<Summary>(`/sessions/${id}/end`, { method: "POST" }),
  analytics: (userId: string, lang?: string) =>
    req<Analytics>(`/users/${userId}/analytics${lang ? `?lang=${lang}` : ""}`),
};

export const LANGUAGES: Record<string, string> = {
  es: "Spanish",
  fr: "French",
  de: "German",
  it: "Italian",
  pt: "Portuguese",
  ja: "Japanese",
  ko: "Korean",
  zh: "Mandarin",
};

/** Anonymous user id persisted in localStorage (MVP: no auth). */
export async function getUserId(): Promise<string> {
  const existing = localStorage.getItem("user_id");
  if (existing) return existing;
  const { id } = await api.createUser("en");
  localStorage.setItem("user_id", id);
  return id;
}

export function playBase64(b64: string | null, mime: string): HTMLAudioElement | null {
  if (!b64) return null;
  const audio = new Audio(`data:${mime};base64,${b64}`);
  audio.play().catch(() => {}); // autoplay can be blocked until a user gesture
  return audio;
}
