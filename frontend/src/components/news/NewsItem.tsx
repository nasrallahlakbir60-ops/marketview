import type { NewsItem as NewsItemType } from "../../types";
import { formatDateTime, formatRelative } from "../../utils/formatDate";

interface NewsItemProps {
  news: NewsItemType;
  now: number;
  labels: Record<string, string>;
  isNew?: boolean;
}

export function NewsItem({ news, now, labels, isNew = false }: NewsItemProps) {
  return (
    <li className={`group border-b border-line/[0.06] last:border-b-0 ${isNew ? "animate-news-in" : ""}`}>
      <a
        className="block rounded-lg px-2 py-3 transition hover:bg-line/[0.04] focus-visible:bg-line/[0.04] focus-visible:outline-none"
        href={news.url}
        rel="noopener noreferrer"
        target="_blank"
      >
        <div className="flex items-center gap-2 text-[11px] text-subtle">
          {isNew && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-label="Nouveau" />}
          <span className="truncate font-medium text-muted">{news.source}</span>
          <span aria-hidden="true">·</span>
          <time className="shrink-0" dateTime={news.published_at} title={formatDateTime(news.published_at)}>
            {formatRelative(news.published_at, now)}
          </time>
        </div>
        <h3 className="mt-1 text-[13px] font-medium leading-5 text-fg group-hover:text-accent">
          {news.title}
          <span className="sr-only"> (s'ouvre dans un nouvel onglet)</span>
        </h3>
        {news.summary && <p className="mt-1 line-clamp-2 text-xs leading-5 text-subtle">{news.summary}</p>}
        {news.currencies.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {news.currencies.map((code) => (
              <span className="rounded border border-line/[0.08] px-1.5 py-0.5 text-[10px] text-muted" key={code}>
                {labels[code] ?? code}
              </span>
            ))}
          </div>
        )}
      </a>
    </li>
  );
}
