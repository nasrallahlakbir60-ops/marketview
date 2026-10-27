import { useEffect } from "react";
import { Link, Navigate, useParams } from "react-router-dom";

import { TimeframeSelector } from "../components/chart/TimeframeSelector";
import { TradingViewWidget } from "../components/chart/TradingViewWidget";
import { ErrorMessage } from "../components/common/ErrorMessage";
import { Loader } from "../components/common/Loader";
import { MacroPanel } from "../components/macro/MacroPanel";
import { NewsPanel } from "../components/news/NewsPanel";
import { PairLogo } from "../components/pairs/PairLogo";
import { usePair } from "../hooks/usePairs";
import { ApiError } from "../services/api";
import { useMarketStore } from "../store/marketStore";

export function MarketPage() {
  const { symbol = "" } = useParams();
  const { data: pair, error, isPending, refetch } = usePair(symbol);
  const timeframe = useMarketStore((state) => state.timeframe);
  const setTimeframe = useMarketStore((state) => state.setTimeframe);
  const selectPair = useMarketStore((state) => state.selectPair);

  useEffect(() => {
    if (pair) selectPair(pair.symbol);
  }, [pair?.symbol, selectPair]);

  if (isPending) {
    return (
      <main className="mx-auto min-h-[calc(100vh-138px)] max-w-[1440px] px-4 py-12 sm:px-8">
        <Loader label="Chargement du marché..." />
      </main>
    );
  }
  if (error instanceof ApiError && error.status === 404) return <Navigate replace to="/" />;
  if (error || !pair) {
    return (
      <main className="mx-auto min-h-[calc(100vh-138px)] max-w-[1440px] px-4 py-12 sm:px-8">
        <ErrorMessage message={error?.message ?? "Marché introuvable."} onRetry={() => void refetch()} />
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-[calc(100vh-138px)] max-w-[1440px] px-4 pb-10 pt-7 sm:px-8">
      <Link className="inline-flex items-center gap-2 text-xs text-subtle transition hover:text-accent" to="/">
        <span aria-hidden="true">←</span> Tous les marchés
      </Link>
      <div className="mb-6 mt-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex items-center gap-4">
          <PairLogo pair={pair} size="lg" />
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">{pair.base} / {pair.quote}</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-[-0.04em] text-fg">{pair.symbol}</h1>
            <p className="mt-1 text-sm text-muted">{pair.name}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-lg border border-line/[0.08] px-3 py-2 text-xs text-muted">{pair.tradingview_symbol}</span>
          <TimeframeSelector onChange={setTimeframe} value={timeframe} />
        </div>
      </div>

      {/* Mobile : chart, puis news, puis macro. Grand écran : chart à gauche, panneaux à droite. */}
      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section aria-label="Graphique" className="min-w-0 rounded-2xl border border-line/[0.07] bg-panel/60 p-2 sm:p-3">
          <TradingViewWidget symbol={pair.tradingview_symbol} timeframe={timeframe} />
        </section>
        <aside aria-label="Actualités et données macroéconomiques" className="min-w-0 space-y-4">
          <NewsPanel key={pair.symbol} pair={pair} />
          <MacroPanel pair={pair} />
        </aside>
      </div>
    </main>
  );
}
