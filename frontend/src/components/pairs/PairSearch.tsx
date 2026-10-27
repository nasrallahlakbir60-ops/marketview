interface PairSearchProps {
  value: string;
  onChange: (value: string) => void;
}

export function PairSearch({ value, onChange }: PairSearchProps) {
  return (
    <label className="flex h-12 w-full items-center gap-3 rounded-xl border border-line/[0.09] bg-panel px-4 transition focus-within:border-accent/50 sm:max-w-[360px]">
      <svg aria-hidden="true" className="h-[18px] w-[18px] shrink-0 text-subtle" fill="none" viewBox="0 0 24 24">
        <circle cx="10.8" cy="10.8" r="6.8" stroke="currentColor" strokeWidth="1.7" />
        <path d="m16 16 4.2 4.2" stroke="currentColor" strokeLinecap="round" strokeWidth="1.7" />
      </svg>
      <input
        className="w-full bg-transparent text-sm text-fg/90 outline-none placeholder:text-subtle"
        onChange={(event) => onChange(event.target.value)}
        placeholder="Rechercher un marché..."
        type="search"
        value={value}
      />
      <kbd className="hidden rounded border border-line/[0.09] px-1.5 py-0.5 text-[10px] text-faint sm:inline">⌘ K</kbd>
    </label>
  );
}
