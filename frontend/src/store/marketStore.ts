import { create } from "zustand";

import type { Timeframe } from "../types";

interface MarketState {
  selectedSymbol: string | null;
  timeframe: Timeframe;
  selectPair: (symbol: string) => void;
  setTimeframe: (timeframe: Timeframe) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  selectedSymbol: null,
  timeframe: "60",
  selectPair: (selectedSymbol) => set({ selectedSymbol }),
  setTimeframe: (timeframe) => set({ timeframe }),
}));
