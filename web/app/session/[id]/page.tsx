"use client";

import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import DifficultyMeter from "@/components/DifficultyMeter";
import Recorder from "@/components/Recorder";
import Transcript, { type Message } from "@/components/Transcript";
import { api, LANGUAGES, playBase64, type Summary, type TurnResult } from "@/lib/api";

export default function SessionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [messages, setMessages] = useState<Message[]>([]);
  const [language, setLanguage] = useState("");
  const [langCode, setLangCode] = useState<string | undefined>(undefined);
  const [difficulty, setDifficulty] = useState(2);
  const [cefr, setCefr] = useState("A2");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [ending, setEnding] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState<Message["id"] | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  function play(b64: string | null, mime: string) {
    audioRef.current?.pause();
    audioRef.current = playBase64(b64, mime);
  }

  // Load the session. A new one has no turns yet: the learner speaks first.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await api.getSession(id);
        if (cancelled) return;
        setLanguage(LANGUAGES[s.target_lang] ?? s.target_lang);
        setLangCode(s.target_lang);
        setDifficulty(s.difficulty.value);
        setCefr(s.difficulty.cefr);
        setMessages(s.turns.map((t) => ({ ...t })));
        if (s.ended) setSummary(await api.endSession(id));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Couldn't load session");
      }
    })();
    return () => {
      cancelled = true;
      audioRef.current?.pause();
    };
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  function applyTurn(userText: string, r: TurnResult) {
    setMessages((prev) => [
      ...prev.filter((m) => m.id !== "pending-user"),
      {
        id: r.user_turn.id,
        role: "user",
        text: r.user_turn.text || userText,
        corrections: r.user_turn.corrections,
        unclear_spans: r.user_turn.features.unclear_spans,
      },
      {
        id: r.assistant_turn.id,
        role: "assistant",
        text: r.assistant_turn.text,
        translation: r.assistant_turn.translation,
        audio: r.audio_b64 ? { b64: r.audio_b64, mime: r.audio_mime } : null,
      },
    ]);
    setDifficulty(r.difficulty.after);
    setCefr(r.difficulty.cefr);
    play(r.audio_b64, r.audio_mime);
  }

  async function playMessage(m: Message) {
    try {
      let audio = m.audio;
      if (!audio) {
        setLoadingAudio(m.id);
        const r = await api.speak(m.text, langCode);
        audio = { b64: r.audio_b64, mime: r.audio_mime };
        const cached = audio;
        setMessages((prev) => prev.map((x) => (x.id === m.id ? { ...x, audio: cached } : x)));
      }
      play(audio.b64, audio.mime);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't play audio");
    } finally {
      setLoadingAudio(null);
    }
  }

  async function submit(send: () => Promise<TurnResult>, optimisticText?: string) {
    setPending(true);
    setError(null);
    if (optimisticText) {
      setMessages((prev) => [...prev, { id: "pending-user", role: "user", text: optimisticText }]);
    }
    try {
      applyTurn(optimisticText ?? "", await send());
    } catch (e) {
      setMessages((prev) => prev.filter((m) => m.id !== "pending-user"));
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setPending(false);
    }
  }

  async function end() {
    setEnding(true);
    try {
      setSummary(await api.endSession(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't end session");
    } finally {
      setEnding(false);
    }
  }

  if (summary) return <SummaryView summary={summary} />;

  return (
    <div className="flex min-h-[calc(100vh-10rem)] flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide opacity-50">Practicing</p>
          <h1 className="text-lg font-semibold">{language || "…"}</h1>
        </div>
        <div className="text-right">
          <p className="mb-1 text-xs opacity-60">Level {cefr}</p>
          <DifficultyMeter value={difficulty} />
        </div>
      </div>

      <div className="flex-1">
        {messages.length === 0 && !pending && (
          <p className="mt-16 text-center opacity-60">
            Hold the button below and say something{language ? ` in ${language}` : ""} to begin. The tutor will reply.
          </p>
        )}
        <Transcript messages={messages} pending={pending} onPlay={playMessage} loadingId={loadingAudio} />
        <div ref={bottomRef} />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="sticky bottom-0 space-y-3 bg-background/90 py-4 backdrop-blur">
        <Recorder disabled={pending} onRecorded={(blob) => submit(() => api.sendAudio(id, blob))} />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const t = draft.trim();
            if (!t || pending) return;
            setDraft("");
            submit(() => api.sendText(id, t), t);
          }}
          className="flex gap-2"
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="…or type your reply"
            className="flex-1 rounded-lg border border-black/15 bg-transparent px-3 py-2 text-sm dark:border-white/20"
          />
          <button disabled={pending || !draft.trim()} className="rounded-lg border border-black/15 px-3 text-sm disabled:opacity-40 dark:border-white/20">
            Send
          </button>
        </form>
        <div className="flex flex-col items-center gap-1">
          <button
            onClick={end}
            disabled={ending || pending || messages.length < 2}
            className="rounded-lg border border-black/20 px-4 py-2 text-sm font-medium transition hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/25 dark:hover:bg-white/10"
          >
            {ending ? "Wrapping up… (can take a few seconds)" : "End session & see summary"}
          </button>
          {messages.length < 2 && <p className="text-xs opacity-60">Say something first to be able to finish the session.</p>}
        </div>
      </div>
    </div>
  );
}

function SummaryView({ summary: s }: { summary: Summary }) {
  const errors = Object.entries(s.errors_by_category).sort((a, b) => b[1] - a[1]);
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Session complete</h1>
        {s.coach_note && <p className="mt-2 opacity-80">{s.coach_note}</p>}
      </div>

      <ProficiencyChange start={s.cefr_start} end={s.cefr_end} change={s.proficiency_change} />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Stat label="Turns" value={s.turns} />
        <Stat label="Words spoken" value={s.words_spoken} />
        <Stat label="Level" value={s.cefr_end} />
        <Stat label="Avg score" value={s.avg_performance != null ? `${Math.round(s.avg_performance * 100)}%` : "–"} />
        {s.avg_clarity != null && <Stat label="Clarity" value={`${Math.round(s.avg_clarity * 100)}%`} />}
      </div>

      {errors.length > 0 && (
        <section>
          <h2 className="mb-2 font-medium">Where you slipped</h2>
          <div className="flex flex-wrap gap-2">
            {errors.map(([cat, n]) => (
              <span key={cat} className="rounded-full bg-amber-500/15 px-3 py-1 text-sm">
                {cat.replace("_", " ")} · {n}
              </span>
            ))}
          </div>
        </section>
      )}

      {s.off_topic_replies.length > 0 && (
        <section>
          <h2 className="mb-2 font-medium">Replies that missed the question · {s.off_topic_count}</h2>
          <ul className="space-y-2">
            {s.off_topic_replies.map((r, i) => (
              <li key={i} className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2">
                <span className="font-medium">&ldquo;{r.text}&rdquo;</span>
                {r.reason && <p className="text-sm opacity-70">{r.reason}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {s.vocab_to_review.length > 0 && (
        <section>
          <h2 className="mb-2 font-medium">Words to review</h2>
          <ul className="grid gap-2 sm:grid-cols-2">
            {s.vocab_to_review.map((v) => (
              <li key={v.lemma} className="rounded-lg border border-black/10 px-3 py-2 dark:border-white/15">
                <span className="font-medium">{v.lemma}</span> {v.cefr && <span className="text-xs opacity-50">{v.cefr}</span>}
                {v.meaning && <p className="text-sm opacity-70">{v.meaning}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex gap-3">
        <Link href="/" className="rounded-lg bg-foreground px-4 py-2 text-background">
          New conversation
        </Link>
        <Link href="/dashboard" className="rounded-lg border border-black/15 px-4 py-2 dark:border-white/20">
          See progress
        </Link>
      </div>
    </div>
  );
}

function ProficiencyChange({ start, end, change }: { start: string; end: string; change: number }) {
  const steady = Math.abs(change) < 0.05;
  const up = change > 0;
  const tone = steady ? "border-black/10 dark:border-white/15" : up ? "border-green-500/40 bg-green-500/10" : "border-red-500/40 bg-red-500/10";
  const label = steady ? "No change" : `${up ? "▲ Up" : "▼ Down"} ${Math.abs(change).toFixed(1)} ${Math.abs(change) === 1 ? "level" : "levels"}`;
  return (
    <section className={`rounded-xl border p-4 ${tone}`}>
      <p className="text-xs opacity-60">Proficiency this session</p>
      <p className="text-xl font-semibold">{label}</p>
      <p className="text-sm opacity-70">
        {start} → {end}
      </p>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-black/10 p-3 dark:border-white/15">
      <p className="text-xs opacity-60">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  );
}
