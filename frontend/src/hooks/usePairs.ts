import { useQuery } from "@tanstack/react-query";

import { api } from "../services/api";

export function usePairs() {
  return useQuery({
    queryKey: ["pairs"],
    queryFn: api.pairs,
    staleTime: 5 * 60_000,
  });
}

export function usePair(symbol: string) {
  return useQuery({
    queryKey: ["pair", symbol.toUpperCase()],
    queryFn: () => api.pair(symbol),
    staleTime: 5 * 60_000,
    enabled: symbol.length > 0,
  });
}
