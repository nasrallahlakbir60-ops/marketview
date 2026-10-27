import type { MacroIndicator } from "../../types";
import { formatPeriod } from "../../utils/formatDate";
import { formatPercent } from "../../utils/formatNumber";

interface InflationCardProps {
  indicator: MacroIndicator;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[10px] uppercase tracking-wide text-subtle">{label}</dt>
      <dd className="mt-0.5 truncate text-xs font-medium text-fg/90">{value}</dd>
    </div>
  );
}

export function InflationCard({ indicator }: InflationCardProps) {
  const isRate = indicator.indicator === "INTEREST_RATE";
  const periodLabel = isRate ? "En vigueur depuis" : indicator.frequency === "annual" ? "Année" : "Période";
  const previousSuffix = indicator.previous_period && !isRate ? ` (${formatPeriod(indicator.previous_period)})` : "";

  return (
    <article className="rounded-xl border border-line/[0.07] bg-line/[0.02] p-3">
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-xs font-medium text-muted">{indicator.label}</h4>
        <span className="text-lg font-semibold tabular-nums tracking-tight text-fg">{formatPercent(indicator.value)}</span>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2">
        <Field label="Précédent" value={`${formatPercent(indicator.previous)}${previousSuffix}`} />
        <Field label="Prévision" value={formatPercent(indicator.forecast)} />
        <Field label={periodLabel} value={formatPeriod(indicator.period)} />
        <Field label="Mis à jour" value={formatPeriod(indicator.release_date)} />
      </dl>
      <p className="mt-2 text-[10px] text-subtle">
        Source :{" "}
        {indicator.source_url ? (
          <a className="underline decoration-line/20 underline-offset-2 hover:text-accent" href={indicator.source_url} rel="noopener noreferrer" target="_blank">
            {indicator.source}
          </a>
        ) : (
          indicator.source
        )}
        {indicator.frequency === "annual" && " · donnée annuelle"}
      </p>
    </article>
  );
}
