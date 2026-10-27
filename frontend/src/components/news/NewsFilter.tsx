import type { NewsTag } from "../../types";

interface NewsFilterProps {
  tags: NewsTag[];
  value: string | null;
  onChange: (value: string | null) => void;
}

export function NewsFilter({ tags, value, onChange }: NewsFilterProps) {
  const options: { code: string | null; label: string }[] = [{ code: null, label: "Tout" }, ...tags];
  return (
    <div aria-label="Filtrer les news" className="flex flex-wrap gap-1" role="group">
      {options.map((option) => (
        <button
          aria-pressed={value === option.code}
          className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition ${
            value === option.code ? "bg-accent text-on-accent" : "border border-line/[0.08] text-muted hover:text-fg"
          }`}
          key={option.code ?? "all"}
          onClick={() => onChange(option.code)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
