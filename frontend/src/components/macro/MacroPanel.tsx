import { useMacro } from "../../hooks/useMacro";
import type { PairDetail } from "../../types";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { Loader } from "../common/Loader";
import { EconomicCalendar } from "./EconomicCalendar";
import { InflationCard } from "./InflationCard";

interface MacroPanelProps {
  pair: PairDetail;
}

function macroContext(pair: PairDetail): string | null {
  if (pair.category === "metal") return "Métaux : on suit les données des États-Unis (USD), référence du marché.";
  if (pair.category === "crypto") return "Crypto : on suit les données des États-Unis (USD).";
  if (pair.category === "index" || pair.category === "commodity") {
    return `Données du pays de la devise de cotation (${pair.quote}).`;
  }
  return null;
}

export function MacroPanel({ pair }: MacroPanelProps) {
  const { data, error, isPending, refetch } = useMacro(pair.symbol);
  const notes = (data?.sources ?? []).filter((source) => source.message);
  const context = macroContext(pair);

  return (
    <section aria-labelledby="macro-title" className="rounded-2xl border border-line/[0.07] bg-panel/70 p-4">
      <h2 className="text-sm font-semibold text-fg" id="macro-title">
        Macro / Inflation
      </h2>
      {context && <p className="mt-1 text-[11px] leading-5 text-subtle">{context}</p>}

      <div className="mt-3 space-y-4">
        {isPending && <Loader label="Chargement des indicateurs..." />}
        {error && <ErrorMessage message={error.message} onRetry={() => void refetch()} />}
        {data?.countries.map((country) => (
          <div key={country.code}>
            <div className="mb-2 flex items-center gap-2">
              <h3 className="text-xs font-semibold text-fg/90">{country.name}</h3>
              <span className="rounded bg-line/[0.06] px-1.5 py-0.5 text-[10px] font-semibold text-muted">{country.currency}</span>
            </div>
            {country.indicators.length > 0 ? (
              <div className="space-y-2">
                {country.indicators.map((indicator) => (
                  <InflationCard indicator={indicator} key={`${indicator.indicator}-${indicator.source}`} />
                ))}
              </div>
            ) : (
              <EmptyState description="Les données seront affichées après la prochaine mise à jour quotidienne." title="—" />
            )}
          </div>
        ))}
        {notes.length > 0 && (
          <p className="text-[11px] leading-5 text-subtle">{notes.map((source) => `${source.name} : ${source.message}`).join(" · ")}</p>
        )}
      </div>

      <div className="mt-5 border-t border-line/[0.06] pt-4">
        <EconomicCalendar symbol={pair.symbol} />
      </div>
    </section>
  );
}
