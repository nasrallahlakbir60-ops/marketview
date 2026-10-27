import { Link } from "react-router-dom";

import type { Pair } from "../../types";
import { PairLogo } from "./PairLogo";

interface PairCardProps {
  pair: Pair;
}

export function PairCard({ pair }: PairCardProps) {
  return (
    <Link
      className="group flex min-h-[104px] items-center justify-between rounded-2xl border border-line/[0.07] bg-panel/70 p-4 transition duration-200 hover:-translate-y-0.5 hover:border-accent/30 hover:bg-panel-hover"
      to={`/market/${encodeURIComponent(pair.symbol)}`}
    >
      <div className="flex items-center gap-3.5">
        <PairLogo pair={pair} />
        <span>
          <span className="block font-semibold tracking-wide text-fg">{pair.symbol}</span>
          <span className="mt-1 block max-w-[190px] truncate text-xs text-subtle">{pair.name}</span>
        </span>
      </div>
      <span className="text-faint transition group-hover:translate-x-0.5 group-hover:text-accent" aria-hidden="true">
        →
      </span>
    </Link>
  );
}
