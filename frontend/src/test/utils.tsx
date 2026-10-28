import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import type { NewsItem, PairDetail } from "../types";

export function renderWithProviders(ui: ReactElement, { route = "/" }: { route?: string } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

/** Remplace fetch : chaque chemin d'API renvoie la réponse JSON associée (ou une erreur HTTP). */
export function mockFetch(routes: Record<string, unknown | { status: number; body?: unknown }>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const entry = routes[url.pathname];
    if (entry === undefined) return new Response(JSON.stringify({ detail: "Introuvable" }), { status: 404 });
    if (entry && typeof entry === "object" && "status" in entry) {
      const { status, body } = entry as { status: number; body?: unknown };
      return new Response(JSON.stringify(body ?? {}), { status });
    }
    return new Response(JSON.stringify(entry), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export const eurusd: PairDetail = {
  symbol: "EURUSD",
  name: "Euro / Dollar US",
  category: "forex_major",
  base: "EUR",
  quote: "USD",
  tradingview_symbol: "OANDA:EURUSD",
  active: true,
  news_tags: [
    { code: "EUR", label: "EUR" },
    { code: "USD", label: "USD" },
  ],
  macro_countries: [
    { code: "EA", name: "Zone euro", currency: "EUR" },
    { code: "US", name: "Etats-Unis", currency: "USD" },
  ],
};

export function makeNews(overrides: Partial<NewsItem> = {}): NewsItem {
  return {
    id: 1,
    title: "ECB keeps rates unchanged",
    summary: "Short summary.",
    url: "https://example.com/ecb",
    source: "BCE",
    image_url: null,
    published_at: new Date(Date.now() - 5 * 60_000).toISOString(),
    currencies: ["EUR"],
    ...overrides,
  };
}
