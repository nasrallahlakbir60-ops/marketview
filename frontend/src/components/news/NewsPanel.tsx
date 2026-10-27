import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useNews } from "../../hooks/useNews";
import { useNewsSocket } from "../../hooks/useNewsSocket";
import { useNow } from "../../hooks/useNow";
import { api } from "../../services/api";
import type { PairDetail } from "../../types";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { Loader } from "../common/Loader";
import { LiveIndicator } from "./LiveIndicator";
import { NewsFilter } from "./NewsFilter";
import { NewsItem } from "./NewsItem";

interface NewsPanelProps {
  pair: PairDetail;
}

export function NewsPanel({ pair }: NewsPanelProps) {
  const [filter, setFilter] = useState<string | null>(null);
  const { data, error, isPending, refetch } = useNews(pair.symbol);
  const { data: sources } = useQuery({ queryKey: ["news-sources"], queryFn: api.newsSources, staleTime: 5 * 60_000 });
  const { status, newIds } = useNewsSocket(pair.symbol);
  const now = useNow();

  const labels = useMemo(() => Object.fromEntries(pair.news_tags.map((tag) => [tag.code, tag.label])), [pair.news_tags]);
  const items = useMemo(
    () => (filter ? (data ?? []).filter((news) => news.currencies.includes(filter)) : data ?? []),
    [data, filter],
  );
  const unavailable = (sources ?? []).filter((source) => source.message);

  return (
    <section aria-labelledby="news-title" className="flex flex-col rounded-2xl border border-line/[0.07] bg-panel/70 p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-fg" id="news-title">
          News
        </h2>
        <div className="flex items-center gap-3">
          {data && <span className="text-[11px] text-subtle">{items.length} articles</span>}
          <LiveIndicator status={status} />
        </div>
      </div>

      {pair.news_tags.length > 1 && (
        <div className="mt-3">
          <NewsFilter onChange={setFilter} tags={pair.news_tags} value={filter} />
        </div>
      )}

      <div className="mt-3 max-h-[560px] min-h-[120px] overflow-y-auto pr-1">
        {isPending && <Loader label="Chargement des news..." />}
        {error && <ErrorMessage message={error.message} onRetry={() => void refetch()} />}
        {data && items.length === 0 && (
          <EmptyState
            description={
              filter
                ? "Aucun article récent pour ce filtre."
                : "Les news apparaîtront ici dès qu'une source publie sur ces devises."
            }
            title="Aucune news pour le moment"
          />
        )}
        {items.length > 0 && (
          <ul>
            {items.map((news) => (
              <NewsItem isNew={newIds.has(news.id)} key={news.id} labels={labels} news={news} now={now} />
            ))}
          </ul>
        )}
      </div>

      {unavailable.length > 0 && (
        <p className="mt-3 border-t border-line/[0.06] pt-3 text-[11px] leading-5 text-subtle">
          {unavailable.map((source) => `${source.name} : ${source.message}`).join(" · ")}
        </p>
      )}
    </section>
  );
}
