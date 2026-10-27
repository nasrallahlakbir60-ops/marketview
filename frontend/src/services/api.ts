import type { CalendarResponse, MacroResponse, NewsItem, Pair, PairDetail, SourceStatus } from "../types";

// Vide en production : le frontend et l'API sont servis par le même domaine (Nginx).
export const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type QueryParams = Record<string, string | number | undefined>;

async function apiGet<T>(path: string, params: QueryParams = {}): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) query.set(key, String(value));
  }
  const url = `${API_URL}${path}${query.size ? `?${query}` : ""}`;

  let response: Response;
  try {
    response = await fetch(url, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError("Impossible de joindre le serveur MarketView. Vérifiez votre connexion.", 0);
  }

  if (!response.ok) {
    let detail = `Erreur du serveur (${response.status}).`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Corps non JSON : on garde le message générique.
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  pairs: () => apiGet<Pair[]>("/api/pairs"),
  pair: (symbol: string) => apiGet<PairDetail>(`/api/pairs/${encodeURIComponent(symbol)}`),
  news: (pair: string, limit = 50) => apiGet<NewsItem[]>("/api/news", { pair, limit }),
  newsSources: () => apiGet<SourceStatus[]>("/api/news/sources"),
  macro: (pair: string) => apiGet<MacroResponse>("/api/macro", { pair }),
  calendar: (pair: string, day = "today") => apiGet<CalendarResponse>("/api/calendar", { pair, day }),
};
