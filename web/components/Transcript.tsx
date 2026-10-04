"use client";

import { useState } from "react";
import type { Correction } from "@/lib/api";

export type Message = {
  id: number | string;
  role: "user" | "assistant";
  text: string;
  translation?: string | null;
  corrections?: Correction[];
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
        <p>{m.text}</p>
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
