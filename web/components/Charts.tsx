"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

const CEFR = ["A1", "A2", "B1", "B2", "C1", "C2"];
const H = 240;
const PAD = { l: 34, r: 16, t: 12, b: 28 };

/** Track the rendered width so the SVG is drawn 1:1 (text stays a readable size on phones). */
function useWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, e.contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

export function ChartCard({
  title,
  subtitle,
  legend,
  table,
  children,
}: {
  title: string;
  subtitle?: string;
  legend?: { label: string; color: string }[];
  table: { head: string[]; rows: (string | number)[][] };
  children: ReactNode;
}) {
  const [showTable, setShowTable] = useState(false);
  return (
    <section className="rounded-xl border border-black/10 p-4 dark:border-white/15" style={{ background: "var(--chart-surface)" }}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-medium" style={{ color: "var(--ink-primary)" }}>
            {title}
          </h2>
          {subtitle && (
            <p className="text-sm" style={{ color: "var(--ink-secondary)" }}>
              {subtitle}
            </p>
          )}
        </div>
        <button onClick={() => setShowTable((s) => !s)} className="shrink-0 text-xs underline" style={{ color: "var(--ink-secondary)" }}>
          {showTable ? "View chart" : "View as table"}
        </button>
      </div>
      {legend && legend.length > 1 && (
        <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs" style={{ color: "var(--ink-secondary)" }}>
          {legend.map((l) => (
            <li key={l.label} className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} />
              {l.label}
            </li>
          ))}
        </ul>
      )}
      {showTable ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" style={{ color: "var(--ink-primary)" }}>
            <thead style={{ color: "var(--ink-secondary)" }}>
              <tr>
                {table.head.map((h) => (
                  <th key={h} className="py-1 pr-4 font-normal">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((r, i) => (
                <tr key={i} className="border-t" style={{ borderColor: "var(--grid)" }}>
                  {r.map((c, j) => (
                    <td key={j} className="py-1 pr-4 tabular-nums">
                      {c}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        children
      )}
    </section>
  );
}

type Tip = { x: number; y: number; title: string; rows: { label: string; value: string; color: string }[] };

function Tooltip({ tip, width }: { tip: Tip | null; width: number }) {
  if (!tip) return null;
  const flip = tip.x > width / 2;
  return (
    <div
      className="pointer-events-none absolute z-10 rounded-lg border px-3 py-2 text-xs shadow-md"
      style={{
        top: Math.max(0, tip.y - 8),
        left: flip ? undefined : tip.x + 12,
        right: flip ? width - tip.x + 12 : undefined,
        background: "var(--chart-surface)",
        borderColor: "var(--axis)",
        color: "var(--ink-secondary)",
      }}
    >
      <p className="mb-1">{tip.title}</p>
      {tip.rows.map((r) => (
        <p key={r.label} className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-3" style={{ background: r.color }} />
          <span className="font-semibold tabular-nums" style={{ color: "var(--ink-primary)" }}>
            {r.value}
          </span>
          <span>{r.label}</span>
        </p>
      ))}
    </div>
  );
}

/* ---------- Difficulty line (single series, y axis in CEFR levels) ---------- */

export function DifficultyLine({ points }: { points: { label: string; value: number; topic: string }[] }) {
  const [ref, w] = useWidth();
  const [hover, setHover] = useState<number | null>(null);
  const iw = w - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const x = (i: number) => PAD.l + (points.length === 1 ? iw / 2 : (i / (points.length - 1)) * iw);
  const y = (v: number) => PAD.t + ih - ((v - 1) / 5) * ih;
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.value)}`).join(" ");
  const area = `${line} L${x(points.length - 1)},${y(1)} L${x(0)},${y(1)} Z`;
  const step = Math.ceil(points.length / 6);

  const at = (clientX: number) => {
    const rect = ref.current!.getBoundingClientRect();
    const rel = clientX - rect.left - PAD.l;
    const i = points.length === 1 ? 0 : Math.round((rel / iw) * (points.length - 1));
    setHover(Math.max(0, Math.min(points.length - 1, i)));
  };

  const tip: Tip | null =
    hover == null
      ? null
      : {
          x: x(hover),
          y: y(points[hover].value),
          title: `${points[hover].label} · ${points[hover].topic}`,
          rows: [
            {
              label: "difficulty",
              value: `${CEFR[Math.round(points[hover].value) - 1]} (${points[hover].value.toFixed(1)})`,
              color: "var(--series-1)",
            },
          ],
        };

  return (
    <div ref={ref} className="relative" onPointerMove={(e) => at(e.clientX)} onPointerLeave={() => setHover(null)}>
      <svg width={w} height={H} role="img" aria-label="Difficulty level by session">
        {CEFR.map((l, i) => (
          <g key={l}>
            <line x1={PAD.l} x2={w - PAD.r} y1={y(i + 1)} y2={y(i + 1)} stroke={i === 0 ? "var(--axis)" : "var(--grid)"} strokeWidth={1} />
            <text x={PAD.l - 8} y={y(i + 1) + 4} textAnchor="end" fontSize={11} fill="var(--ink-muted)">
              {l}
            </text>
          </g>
        ))}
        {points.map((p, i) =>
          i % step === 0 || i === points.length - 1 ? (
            <text key={i} x={x(i)} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--ink-muted)">
              {p.label}
            </text>
          ) : null,
        )}
        {points.length > 1 && <path d={area} fill="var(--series-1)" opacity={0.1} />}
        {points.length > 1 && <path d={line} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={PAD.t + ih} stroke="var(--axis)" strokeWidth={1} />}
        {points.map((p, i) => (
          <circle key={i} cx={x(i)} cy={y(p.value)} r={hover === i ? 5 : 4} fill="var(--series-1)" stroke="var(--chart-surface)" strokeWidth={2} />
        ))}
      </svg>
      <Tooltip tip={tip} width={w} />
    </div>
  );
}

/* ---------- Errors per session (stacked columns) ---------- */

export type StackDatum = { label: string; topic: string; segments: Record<string, number> };

function topRounded(x: number, y: number, w: number, h: number, r: number) {
  r = Math.min(r, h / 2, w / 2);
  return `M${x},${y + h} L${x},${y + r} Q${x},${y} ${x + r},${y} L${x + w - r},${y} Q${x + w},${y} ${x + w},${y + r} L${x + w},${y + h} Z`;
}

export function ErrorStack({ data, keys }: { data: StackDatum[]; keys: { key: string; label: string; color: string }[] }) {
  const [ref, w] = useWidth();
  const [hover, setHover] = useState<{ i: number; px: number; py: number } | null>(null);
  const iw = w - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const totals = data.map((d) => keys.reduce((s, k) => s + (d.segments[k.key] ?? 0), 0));
  const max = Math.max(4, ...totals);
  const stepY = max <= 8 ? 2 : Math.ceil(max / 4 / 5) * 5;
  const top = Math.ceil(max / stepY) * stepY;
  const y = (v: number) => PAD.t + ih - (v / top) * ih;
  const band = iw / data.length;
  const bw = Math.min(24, band * 0.6);
  const ticks = Array.from({ length: top / stepY + 1 }, (_, i) => i * stepY);
  const labelStep = Math.ceil(data.length / 6);

  const tipFor = (i: number): Tip => ({
    x: PAD.l + band * i + band / 2,
    y: y(totals[i]),
    title: `${data[i].label} · ${data[i].topic}`,
    rows: [
      ...keys.filter((k) => data[i].segments[k.key]).map((k) => ({ label: k.label, value: String(data[i].segments[k.key]), color: k.color })),
      ...(totals[i] === 0 ? [{ label: "no mistakes", value: "0", color: "var(--axis)" }] : []),
    ],
  });

  return (
    <div ref={ref} className="relative" onPointerLeave={() => setHover(null)}>
      <svg width={w} height={H} role="img" aria-label="Mistakes per session by category">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={w - PAD.r} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} strokeWidth={1} />
            <text x={PAD.l - 8} y={y(t) + 4} textAnchor="end" fontSize={11} fill="var(--ink-muted)">
              {t}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const cx = PAD.l + band * i + band / 2;
          let acc = 0;
          const present = keys.filter((k) => d.segments[k.key]);
          return (
            <g
              key={i}
              tabIndex={0}
              onFocus={() => setHover({ i, px: 0, py: 0 })}
              onBlur={() => setHover(null)}
              onPointerMove={() => setHover({ i, px: 0, py: 0 })}
              style={{ outline: "none" }}
            >
              <rect x={PAD.l + band * i} y={PAD.t} width={band} height={ih} fill="transparent" />
              {hover?.i === i && <rect x={PAD.l + band * i} y={PAD.t} width={band} height={ih} fill="var(--ink-primary)" opacity={0.05} />}
              {present.map((k, si) => {
                const v = d.segments[k.key];
                const y0 = y(acc);
                acc += v;
                const y1 = y(acc);
                const gap = si === 0 ? 0 : 2; // 2px surface gap between stacked segments
                const h = Math.max(1, y0 - y1 - gap);
                const isTop = si === present.length - 1;
                return isTop ? (
                  <path key={k.key} d={topRounded(cx - bw / 2, y1, bw, h, 4)} fill={k.color} />
                ) : (
                  <rect key={k.key} x={cx - bw / 2} y={y1 + gap} width={bw} height={h} fill={k.color} />
                );
              })}
              {(i % labelStep === 0 || i === data.length - 1) && (
                <text x={cx} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--ink-muted)">
                  {d.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <Tooltip tip={hover ? tipFor(hover.i) : null} width={w} />
    </div>
  );
}
