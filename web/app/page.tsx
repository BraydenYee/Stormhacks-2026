"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getUserId, LANGUAGES } from "@/lib/api";

const LEVELS = [
  { value: "a1", label: "A1 — Beginner" },
  { value: "a2", label: "A2 — Elementary" },
  { value: "b1", label: "B1 — Intermediate" },
  { value: "b2", label: "B2 — Upper intermediate" },
  { value: "c1", label: "C1 — Advanced" },
  { value: "c2", label: "C2 — Proficient" },
];

type Suggested = { cefr: string; exists: boolean };

export default function Home() {
  const router = useRouter();
  const [lang, setLang] = useState("es");
  const [suggested, setSuggested] = useState<Suggested | null>(null);
  const [picked, setPicked] = useState<string | null>(null); // set only when the learner changes the level
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preselect the language from config.toml. Best effort: the page works without it.
  useEffect(() => {
    api
      .config()
      .then((c) => {
        if (c.language && c.language in LANGUAGES) setLang(c.language);
      })
      .catch(() => {});
  }, []);

  // The learner's estimated level in this language (or, for a new learner, where they would start).
  useEffect(() => {
    let cancelled = false;
    getUserId()
      .then((id) => api.level(id, lang))
      .then((l) => {
        if (!cancelled) setSuggested({ cefr: l.cefr.toLowerCase(), exists: l.exists });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [lang]);

  const shown = picked ?? suggested?.cefr ?? "";

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const userId = await getUserId();
      // Only send a level when the learner overrode the suggestion. Otherwise the server continues from the
      // exact stored level, which is finer-grained than the A1–C2 label shown here.
      const override = picked && picked !== suggested?.cefr ? picked : undefined;
      const s = await api.startSession(userId, lang, override);
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
            onChange={(e) => {
              setLang(e.target.value);
              setPicked(null);
              setSuggested(null);
            }}
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
          <span className="text-sm font-medium">Level</span>
          <select
            value={shown}
            onChange={(e) => setPicked(e.target.value)}
            className="w-full rounded-lg border border-black/15 bg-transparent px-3 py-2 dark:border-white/20"
          >
            {shown === "" && (
              <option value="" className="text-black">
                Checking your level…
              </option>
            )}
            {LEVELS.map((l) => (
              <option key={l.value} value={l.value} className="text-black">
                {l.label}
                {suggested?.cefr === l.value ? (suggested.exists ? " (Current Predicted Level)" : " (suggested start)") : ""}
              </option>
            ))}
          </select>
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
