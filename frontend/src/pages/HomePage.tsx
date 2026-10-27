import { useMemo, useState } from "react";

import { ErrorMessage } from "../components/common/ErrorMessage";
import { Loader } from "../components/common/Loader";
import { PairCard } from "../components/pairs/PairCard";
import { PairSearch } from "../components/pairs/PairSearch";
import { usePairs } from "../hooks/usePairs";
import type { Pair } from "../types";

const categoryLabels: Record<string, string> = {
  forex_major: "Forex · Majeures",
  forex_cross: "Forex · Croisées",
  forex_exotic: "Forex · Exotiques",
  metal: "Métaux",
  commodity: "Matières premières",
  index: "Indices",
  crypto: "Crypto",
};

const categoryOrder = Object.keys(categoryLabels);

export function HomePage() {
  const [search, setSearch] = useState("");
  const { data, error, isPending, refetch } = usePairs();

  const groups = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("fr");
    const filtered = (data ?? []).filter((pair) => {
      if (!pair.active) return false;
      return !query || `${pair.symbol} ${pair.name} ${pair.base} ${pair.quote}`.toLocaleLowerCase("fr").includes(query);
    });
    const grouped = new Map<string, Pair[]>();
    for (const pair of filtered) {
      const current = grouped.get(pair.category) ?? [];
      current.push(pair);
      grouped.set(pair.category, current);
    }
    return categoryOrder
      .filter((category) => grouped.has(category))
      .map((category) => [category, grouped.get(category) ?? []] as const);
  }, [data, search]);

  return (
    <main className="mx-auto min-h-[calc(100vh-138px)] max-w-[1440px] px-5 pb-16 pt-9 sm:px-8 sm:pt-14">
      <section className="relative overflow-hidden rounded-3xl border border-line/[0.07] bg-panel px-6 py-8 sm:px-10 sm:py-11">
        <div className="pointer-events-none absolute -right-10 -top-32 h-80 w-80 rounded-full bg-accent/[0.08] blur-[90px]" />
        <div className="relative">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/[0.06] px-3 py-1.5 text-[11px] font-medium tracking-wide text-accent">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            VOTRE ESPACE DE MARCHÉ
          </div>
          <h1 className="max-w-2xl text-3xl font-semibold leading-tight tracking-[-0.045em] text-fg sm:text-[42px]">
            Gardez un œil sur les marchés.
            <span className="block text-muted">Tout commence par un symbole.</span>
          </h1>
          <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <PairSearch onChange={setSearch} value={search} />
            <p className="text-xs text-subtle">
              <span className="font-semibold text-fg/80">{data?.length ?? "—"}</span> marchés disponibles
            </p>
          </div>
        </div>
      </section>

      <div className="mt-10">
        {isPending && <Loader className="py-12" label="Chargement des marchés..." />}
        {error && <ErrorMessage message={error.message} onRetry={() => void refetch()} />}
        {!isPending && !error && groups.length === 0 && (
          <p className="py-12 text-center text-sm text-muted">Aucun marché ne correspond à « {search} ».</p>
        )}
        <div className="space-y-10">
          {groups.map(([category, pairs]) => (
            <section aria-labelledby={`category-${category}`} key={category}>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold tracking-wide text-fg/90" id={`category-${category}`}>
                  {categoryLabels[category]}
                </h2>
                <span className="text-xs text-faint">{pairs.length} marchés</span>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {pairs.map((pair) => <PairCard key={pair.symbol} pair={pair} />)}
              </div>
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}
