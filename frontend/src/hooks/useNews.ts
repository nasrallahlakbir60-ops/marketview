import { useQuery } from "@tanstack/react-query";

import { api } from "../services/api";

export const NEWS_LIMIT = 50;

export function newsQueryKey(symbol: string) {
  return ["news", symbol.toUpperCase()] as const;
}

/** poll : recharge toutes les 60 s quand le temps réel (WebSocket) n'est pas disponible. */
export function useNews(symbol: string, poll = false) {
  return useQuery({
    queryKey: newsQueryKey(symbol),
    queryFn: () => api.news(symbol, NEWS_LIMIT),
    staleTime: 60_000,
    refetchInterval: poll ? 60_000 : false,
  });
}
