import { useQuery } from "@tanstack/react-query";

import { api } from "../services/api";

export type CalendarDay = "yesterday" | "today" | "tomorrow";

export function useMacro(symbol: string) {
  return useQuery({
    queryKey: ["macro", symbol.toUpperCase()],
    queryFn: () => api.macro(symbol),
    staleTime: 30 * 60_000,
  });
}

export function useCalendar(symbol: string, day: CalendarDay) {
  return useQuery({
    queryKey: ["calendar", symbol.toUpperCase(), day],
    queryFn: () => api.calendar(symbol, day),
    staleTime: 10 * 60_000,
    refetchInterval: 15 * 60_000,
  });
}
