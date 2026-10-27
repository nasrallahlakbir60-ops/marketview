import { useState } from "react";

import { useCalendar, type CalendarDay } from "../../hooks/useMacro";
import type { EconomicEvent, Impact } from "../../types";
import { formatTime } from "../../utils/formatDate";
import { formatWithUnit } from "../../utils/formatNumber";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { Loader } from "../common/Loader";

const impactStyles: Record<Impact, { label: string; className: string }> = {
  low: { label: "Faible", className: "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300" },
  medium: { label: "Moyen", className: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300" },
  high: { label: "Fort", className: "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300" },
};

export function ImpactBadge({ impact }: { impact: Impact }) {
  const style = impactStyles[impact] ?? impactStyles.low;
  return (
    <span className={`inline-flex shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium ${style.className}`}>
      {style.label}
    </span>
  );
}

function EventRow({ event }: { event: EconomicEvent }) {
  return (
    <li className="border-b border-line/[0.06] py-2.5 last:border-b-0">
      <div className="flex items-center gap-2 text-[11px]">
        <time className="w-11 shrink-0 tabular-nums text-muted" dateTime={event.event_time}>
          {formatTime(event.event_time)}
        </time>
        <span className="rounded bg-line/[0.06] px-1.5 py-0.5 text-[10px] font-semibold text-fg/80">{event.currency ?? event.country}</span>
        <ImpactBadge impact={event.impact} />
      </div>
      <p className="mt-1 text-xs font-medium leading-5 text-fg">{event.event_name}</p>
      <dl className="mt-1 grid grid-cols-3 gap-2 text-[10px] text-subtle">
        <div>
          <dt>Réel</dt>
          <dd className="font-medium tabular-nums text-fg/90">{formatWithUnit(event.actual, event.unit)}</dd>
        </div>
        <div>
          <dt>Prévision</dt>
          <dd className="font-medium tabular-nums text-fg/90">{formatWithUnit(event.forecast, event.unit)}</dd>
        </div>
        <div>
          <dt>Précédent</dt>
          <dd className="font-medium tabular-nums text-fg/90">{formatWithUnit(event.previous, event.unit)}</dd>
        </div>
      </dl>
    </li>
  );
}

export function EconomicCalendar({ symbol }: { symbol: string }) {
  const [day, setDay] = useState<CalendarDay>("today");
  const { data, error, isPending, refetch } = useCalendar(symbol, day);

  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Calendrier économique</h3>
        <div aria-label="Jour" className="flex gap-1" role="group">
          {(["today", "tomorrow"] as const).map((value) => (
            <button
              aria-pressed={day === value}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition ${
                day === value ? "bg-accent text-on-accent" : "border border-line/[0.08] text-muted hover:text-fg"
              }`}
              key={value}
              onClick={() => setDay(value)}
              type="button"
            >
              {value === "today" ? "Aujourd'hui" : "Demain"}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-2">
        {isPending && <Loader label="Chargement du calendrier..." />}
        {error && <ErrorMessage message={error.message} onRetry={() => void refetch()} />}
        {data && !data.source.configured && (
          <EmptyState description="Ajoutez FINNHUB_API_KEY dans le fichier .env pour afficher le calendrier." title="Source non configurée" />
        )}
        {data && data.source.configured && data.events.length === 0 && (
          <EmptyState
            description={data.source.message ?? `Aucune annonce prévue pour ${data.currencies.join(" / ")} (journée UTC).`}
            title={data.source.message ? "Calendrier indisponible" : "Aucun événement"}
          />
        )}
        {data && data.events.length > 0 && (
          <ul aria-label="Événements économiques">
            {data.events.map((event) => (
              <EventRow event={event} key={`${event.event_time}-${event.country}-${event.event_name}`} />
            ))}
          </ul>
        )}
      </div>
      {data && data.events.length > 0 && <p className="mt-2 text-[10px] text-subtle">Source : Finnhub · heures locales</p>}
    </div>
  );
}
