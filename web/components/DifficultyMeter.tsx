const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];

/** Live difficulty readout: a bar across A1–C2 with a marker at the current level. */
export default function DifficultyMeter({ value }: { value: number }) {
  const pct = ((Math.min(6, Math.max(1, value)) - 1) / 5) * 100;
  return (
    <div className="w-44" title={`Difficulty ${value.toFixed(2)}`}>
      <div className="relative h-2 rounded-full bg-black/10 dark:bg-white/15">
        <div
          className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-blue-600 transition-all duration-500"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] opacity-60">
        {LEVELS.map((l) => (
          <span key={l}>{l}</span>
        ))}
      </div>
    </div>
  );
}
