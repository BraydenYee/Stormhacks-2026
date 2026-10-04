"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getUserId, LANGUAGES, type AppConfig } from "@/lib/api";

const LEVELS = [
  { value: "", label: "Auto — continue from my current level" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

export default function Home() {
  const router = useRouter();
  const [lang, setLang] = useState("es");
  const [level, setLevel] = useState("");
  const [cfg, setCfg] = useState<AppConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preselect the language from the shared config.toml. Best effort: the page works without it.
  useEffect(() => {
    api
      .config()
      .then((c) => {
        setCfg(c);
        if (c.language && c.language in LANGUAGES) setLang(c.language);
      })
      .catch(() => {});
  }, []);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const userId = await getUserId();
      const s = await api.startSession(userId, lang, level || undefined);
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

        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Starting level</span>
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="w-full rounded-lg border border-black/15 bg-transparent px-3 py-2 dark:border-white/20"
          >
            {LEVELS.map((l) => (
              <option key={l.value} value={l.value} className="text-black">
                {l.label}
              </option>
            ))}
          </select>
          {cfg?.level && <span className="block text-xs opacity-60">New learners start at “{cfg.level}” (from config.toml).</span>}
        </label>

        <button
          onClick={start}
          disabled={busy}
          className="w-full rounded-lg bg-foreground px-4 py-3 font-medium text-background transition disabled:opacity-50"
        >
          {busy ? "Starting…" : "Start conversation"}
        </button>
        <p className="text-center text-xs opacity-60">You speak first. Say anything you like, and the tutor will answer.</p>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
}
