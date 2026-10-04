"use client";

import { useState, type ReactNode } from "react";
import type { Correction, Span } from "@/lib/api";

/** Underlines the stretches of a spoken message that the speech recognizer was unsure of. */
function Highlighted({ text, spans }: { text: string; spans?: Span[] }) {
  if (!spans?.length) return <>{text}</>;
  const parts: ReactNode[] = [];
  let pos = 0;
  spans.forEach(([start, end], i) => {
    if (start < pos) return;
    parts.push(text.slice(pos, start));
    parts.push(
      <span key={i} title="Hard to make out" className="underline decoration-amber-300 decoration-dotted decoration-2 underline-offset-4">
        {text.slice(start, end)}
      </span>,
    );
    pos = end;
  });
  parts.push(text.slice(pos));
  return <>{parts}</>;
}

export type Message = {
  id: number | string;
  role: "user" | "assistant";
  text: string;
  translation?: string | null;
  corrections?: Correction[];
  /** Character ranges the speech recognizer was unsure of (spoken learner messages only). */
  unclear_spans?: Span[];
  /** Cached TTS audio for tutor lines; fetched on demand when missing. */
  audio?: { b64: string; mime: string } | null;
};

function Bubble({ m, onPlay, loading }: { m: Message; onPlay?: (m: Message) => void; loading: boolean }) {
  const [showTranslation, setShowTranslation] = useState(false);
  const mine = m.role === "user";
  return (
    <div className={`flex flex-col gap-1.5 ${mine ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
          mine ? "bg-blue-600 text-white" : "bg-black/5 dark:bg-white/10"
        }`}
      >
        <p>
          <Highlighted text={m.text} spans={m.unclear_spans} />
        </p>
        {!mine && (
          <div className="mt-1 flex gap-3 text-xs">
            {onPlay && (
              <button onClick={() => onPlay(m)} disabled={loading} className="underline opacity-60 hover:opacity-100 disabled:opacity-40">
                {loading ? "Loading audio…" : "▶ Play"}
              </button>
            )}
            {m.translation && (
              <button onClick={() => setShowTranslation((s) => !s)} className="underline opacity-60 hover:opacity-100">
                {showTranslation ? "Hide translation" : "Translate"}
              </button>
            )}
          </div>
        )}
        {showTranslation && <p className="mt-1 text-sm italic opacity-70">{m.translation}</p>}
      </div>
      {mine && !!m.unclear_spans?.length && (
        <p className="max-w-[85%] text-xs opacity-60">Dotted words were hard to make out. Try saying them more clearly.</p>
      )}
      {mine &&
        m.corrections?.map((c, i) => (
          <div
            key={i}
            className="max-w-[85%] rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-sm"
          >
            <span className="line-through opacity-60">{c.original}</span> → <span className="font-medium">{c.corrected}</span>
            <p className="text-xs opacity-70">{c.explanation}</p>
          </div>
        ))}
    </div>
  );
}

export default function Transcript({
  messages,
  pending,
  onPlay,
  loadingId,
}: {
  messages: Message[];
  pending?: boolean;
  onPlay?: (m: Message) => void;
  loadingId?: Message["id"] | null;
}) {
  return (
    <div className="space-y-4">
      {messages.map((m) => (
        <Bubble key={m.id} m={m} onPlay={onPlay} loading={loadingId === m.id} />
      ))}
      {pending && <p className="animate-pulse text-sm opacity-60">Tutor is thinking…</p>}
    </div>
  );
}
