import type { Timeframe, TimeframeOption } from "../../types";

const timeframes: TimeframeOption[] = [
  { label: "1m", value: "1" },
  { label: "5m", value: "5" },
  { label: "15m", value: "15" },
  { label: "1h", value: "60" },
  { label: "4h", value: "240" },
  { label: "1J", value: "D" },
];

interface TimeframeSelectorProps {
  value: Timeframe;
  onChange: (value: Timeframe) => void;
}

export function TimeframeSelector({ value, onChange }: TimeframeSelectorProps) {
  return (
    <div aria-label="Unité de temps" className="flex flex-wrap items-center gap-1" role="group">
      {timeframes.map((timeframe) => (
        <button
          aria-pressed={value === timeframe.value}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            value === timeframe.value ? "bg-accent text-on-accent" : "text-muted hover:bg-line/[0.06] hover:text-fg"
          }`}
          key={timeframe.value}
          onClick={() => onChange(timeframe.value)}
          type="button"
        >
          {timeframe.label}
        </button>
      ))}
    </div>
  );
}
