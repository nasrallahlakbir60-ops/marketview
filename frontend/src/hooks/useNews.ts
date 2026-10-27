import { useQuery } from "@tanstack/react-query";

import { api } from "../services/api";

export const NEWS_LIMIT = 50;

export function newsQueryKey(symbol: string) {
  return ["news", symbol.toUpperCase()] as const;
}

export function useNews(symbol: string) {
  return useQuery({
    queryKey: newsQueryKey(symbol),
    queryFn: () => api.news(symbol, NEWS_LIMIT),
    staleTime: 60_000,
  });
}
