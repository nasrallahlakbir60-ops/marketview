import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { mockFetch, renderWithProviders } from "../test/utils";
import type { Pair } from "../types";
import { HomePage } from "./HomePage";

const pairs: Pair[] = [
  { symbol: "EURUSD", name: "Euro / Dollar US", category: "forex_major", base: "EUR", quote: "USD", tradingview_symbol: "OANDA:EURUSD", active: true },
  { symbol: "XAUUSD", name: "Or / Dollar US", category: "metal", base: "XAU", quote: "USD", tradingview_symbol: "OANDA:XAUUSD", active: true },
];

describe("HomePage", () => {
  it("charge les paires depuis l'API et permet la recherche", async () => {
    const fetchMock = mockFetch({ "/api/pairs": pairs });

    renderWithProviders(<HomePage />);

    expect(screen.getByRole("status")).toHaveTextContent("Chargement des marchés");
    expect(await screen.findByText("EURUSD")).toBeInTheDocument();
    expect(screen.getByText("Métaux")).toBeInTheDocument();
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/pairs");

    fireEvent.change(screen.getByPlaceholderText("Rechercher un marché..."), { target: { value: "or" } });
    expect(screen.queryByText("EURUSD")).not.toBeInTheDocument();
    expect(screen.getByText("XAUUSD")).toBeInTheDocument();
  });

  it("affiche un message d'erreur si l'API est injoignable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));

    renderWithProviders(<HomePage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible de joindre le serveur MarketView");
  });
});
