"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, getUserId, LANGUAGES } from "@/lib/api";

const STARTERS = [
  "Introducing yourself and daily life",
  "Ordering at a café",
  "Hobbies and free time",
  "Your last vacation",
];

export default function Home() {
  const router = useRouter();
  const [lang, setLang] = useState("es");
  const [topic, setTopic] = useState(STARTERS[0]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const userId = await getUserId();
      const s = await api.startSession(userId, lang, topic);
      // Stash the opener so the session page can show and play it without a second request.
      sessionStorage.setItem(`opener:${s.session_id}`, JSON.stringify(s));
      router.push(`/session/${s.session_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Learn by talking.</h1>
        <p className="opacity-70">
          Have a real spoken conversation. The tutor adapts its pace and vocabulary to how you&apos;re doing.
        </p>
      </div>

      <div className="space-y-5">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">I want to practice</span>
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            className="w-full rounded-lg border border-black/15 bg-transparent px-3 py-2 dark:border-white/20"
          >
            {Object.entries(LANGUAGES).map(([code, name]) => (
              <option key={code} value={code} className="text-black">
                {name}
              </option>
            ))}
          </select>
        </label>

        <div className="space-y-1.5">
          <span className="text-sm font-medium">Topic</span>
          <div className="flex flex-wrap gap-2">
            {STARTERS.map((t) => (
              <button
                key={t}
                onClick={() => setTopic(t)}
                className={`rounded-full border px-3 py-1.5 text-sm transition ${
                  topic === t
                    ? "border-transparent bg-foreground text-background"
                    : "border-black/15 hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="…or type your own"
            className="mt-2 w-full rounded-lg border border-black/15 bg-transparent px-3 py-2 dark:border-white/20"
          />
        </div>

        <button
          onClick={start}
          disabled={busy || !topic.trim()}
          className="w-full rounded-lg bg-foreground px-4 py-3 font-medium text-background transition disabled:opacity-50"
        >
          {busy ? "Starting…" : "Start conversation"}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
}
