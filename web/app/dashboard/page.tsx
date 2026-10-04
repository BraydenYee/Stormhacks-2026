"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChartCard, ErrorStack, TrendLine } from "@/components/Charts";
import { api, getUserId, LANGUAGES, type Analytics } from "@/lib/api";

type Full = Extract<Analytics, { empty: false }>;

const CEFR = ["A1", "A2", "B1", "B2", "C1", "C2"];
const pct = (v: number) => `${Math.round(v * 100)}%`;

// Fixed entity → slot mapping so a category keeps its color regardless of what else is present.
const ERROR_KEYS = [
  { key: "grammar", label: "Grammar", color: "var(--series-1)" },
  { key: "vocabulary", label: "Vocabulary", color: "var(--series-2)" },
  { key: "conjugation", label: "Conjugation", color: "var(--series-3)" },
  { key: "word_order", label: "Word order", color: "var(--series-4)" },
  { key: "other", label: "Other", color: "var(--series-other)" },
];

function foldErrors(errors: Record<string, number>) {
  const out: Record<string, number> = {};
  for (const [cat, n] of Object.entries(errors)) {
    const k = ERROR_KEYS.some((e) => e.key === cat) ? cat : "other";
    out[k] = (out[k] ?? 0) + n;
  }
  return out;
}

export default function Dashboard() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setData(await api.analytics(await getUserId()));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Couldn't load analytics");
      }
    })();
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="opacity-60">Loading…</p>;
  if (data.empty)
    return (
      <div className="space-y-3">
        <h1 className="text-2xl font-semibold">No progress yet</h1>
        <p className="opacity-70">Finish a conversation and your stats will show up here.</p>
        <Link href="/" className="inline-block rounded-lg bg-foreground px-4 py-2 text-background">
          Start talking
        </Link>
      </div>
    );

  const d: Full = data;
  const sessions = d.sessions.map((s, i) => ({ ...s, label: `#${i + 1}`, day: new Date(s.date).toLocaleDateString() }));
  const usedKeys = ERROR_KEYS.filter((k) => sessions.some((s) => foldErrors(s.errors)[k.key]));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm opacity-60">{LANGUAGES[d.lang] ?? d.lang} · current level</p>
          <p className="text-5xl font-semibold tracking-tight">{d.difficulty.cefr}</p>
        </div>
        <div className="flex gap-6 text-sm">
          <Stat label="Sessions" value={d.totals.sessions} />
          <Stat label="Turns" value={d.totals.turns} />
          <Stat label="Mistakes logged" value={d.totals.mistakes} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Difficulty over time"
          subtitle="Where the tutor ended each session, on the A1–C2 scale"
          table={{
            head: ["Session", "Date", "Start", "End"],
            rows: sessions.map((s) => [s.label, s.day, s.difficulty_start.toFixed(2), s.difficulty_end.toFixed(2)]),
          }}
        >
          <TrendLine
            points={sessions.map((s) => ({ label: s.label, value: s.difficulty_end, detail: s.day }))}
            min={1}
            max={6}
            ticks={CEFR.map((label, i) => ({ value: i + 1, label }))}
            seriesLabel="difficulty"
            format={(v) => `${CEFR[Math.round(v) - 1]} (${v.toFixed(1)})`}
            ariaLabel="Difficulty level by session"
          />
        </ChartCard>

        <ChartCard
          title="Mistakes per session"
          subtitle="By category"
          legend={usedKeys.map((k) => ({ label: k.label, color: k.color }))}
          table={{
            head: ["Session", "Date", ...ERROR_KEYS.map((k) => k.label)],
            rows: sessions.map((s) => {
              const f = foldErrors(s.errors);
              return [s.label, s.day, ...ERROR_KEYS.map((k) => f[k.key] ?? 0)];
            }),
          }}
        >
          <ErrorStack
            keys={usedKeys}
            data={sessions.map((s) => ({ label: s.label, detail: s.day, segments: foldErrors(s.errors) }))}
          />
        </ChartCard>

        <div className="lg:col-span-2">
          <ChartCard
            title="Pronunciation clarity"
            subtitle="How easily the speech recognizer understood your words, averaged over spoken turns. Typed turns aren't counted."
            table={{
              head: ["Session", "Date", "Clarity", "Unclear words"],
              rows: sessions.map((s) => [s.label, s.day, s.clarity == null ? "–" : pct(s.clarity), s.unclear_words]),
            }}
          >
            <TrendLine
              points={sessions.map((s) => ({ label: s.label, value: s.clarity, detail: s.day }))}
              min={0}
              max={1}
              ticks={[0, 0.25, 0.5, 0.75, 1].map((v) => ({ value: v, label: pct(v) }))}
              seriesLabel="clarity"
              format={pct}
              ariaLabel="Pronunciation clarity by session"
              color="var(--series-3)"
            />
          </ChartCard>
        </div>
      </div>

      <section>
        <h2 className="mb-2 font-medium">Recurring weak spots</h2>
        {d.weak_spots.length === 0 ? (
          <p className="text-sm opacity-60">Not enough mistakes yet to spot patterns — keep talking.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {d.weak_spots.map((w, i) => (
              <div key={i} className="rounded-xl border border-black/10 p-4 dark:border-white/15">
                <div className="flex items-baseline justify-between gap-2">
                  <h3 className="font-medium">{w.label}</h3>
                  <span className="text-xs opacity-60">{w.size}×</span>
                </div>
                <ul className="mt-2 space-y-1 text-sm">
                  {w.examples.map((e, j) => (
                    <li key={j}>
                      <span className="line-through opacity-60">{e.original}</span> → <span className="font-medium">{e.corrected}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 font-medium">Words to review</h2>
        {d.vocab_to_review.length === 0 ? (
          <p className="text-sm opacity-60">Nothing to review yet.</p>
        ) : (
          <ul className="divide-y divide-black/10 rounded-xl border border-black/10 dark:divide-white/15 dark:border-white/15">
            {d.vocab_to_review.map((v) => (
              <li key={v.lemma} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <div>
                  <span className="font-medium">{v.lemma}</span> {v.cefr && <span className="text-xs opacity-50">{v.cefr}</span>}
                  {v.meaning && <p className="opacity-70">{v.meaning}</p>}
                </div>
                <span className="shrink-0 text-xs opacity-60">
                  {v.times_misused > 0 ? `${v.times_misused} slip${v.times_misused > 1 ? "s" : ""}` : "heard, not used"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-2xl font-semibold">{value}</p>
      <p className="text-xs opacity-60">{label}</p>
    </div>
  );
}
