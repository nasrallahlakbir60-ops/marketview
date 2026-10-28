import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { eurusd, mockFetch, renderWithProviders } from "../../test/utils";
import type { CalendarResponse, MacroIndicator, MacroResponse } from "../../types";
import { InflationCard } from "./InflationCard";
import { MacroPanel } from "./MacroPanel";

const cpi: MacroIndicator = {
  country: "US",
  indicator: "CPI",
  label: "Inflation (IPC, sur 12 mois)",
  value: 3,
  previous: 2.5,
  forecast: null,
  period: "2026-09",
  previous_period: "2026-08",
  frequency: "monthly",
  release_date: "2026-10-15",
  source: "FRED",
  source_url: "https://fred.stlouisfed.org/series/CPIAUCSL",
};

const macro: MacroResponse = {
  pair: "EURUSD",
  countries: [
    { code: "EA", name: "Zone euro", currency: "EUR", indicators: [] },
    { code: "US", name: "Etats-Unis", currency: "USD", indicators: [cpi] },
  ],
  sources: [
    { name: "FRED", configured: true, message: null },
    { name: "Banque mondiale", configured: true, message: null },
  ],
};

const calendar = (overrides: Partial<CalendarResponse> = {}): CalendarResponse => ({
  pair: "EURUSD",
  day: "2026-10-27",
  currencies: ["EUR", "USD"],
  events: [
    { country: "US", currency: "USD", event_name: "CPI YoY", impact: "high", actual: null, forecast: 2.9, previous: 3, unit: "%", event_time: "2026-10-27T12:30:00Z" },
    { country: "EA", currency: "EUR", event_name: "ECB speech", impact: "low", actual: null, forecast: null, previous: null, unit: null, event_time: "2026-10-27T08:00:00Z" },
  ],
  source: { name: "ForexFactory", configured: true, message: null },
  ...overrides,
});

describe("InflationCard", () => {
  it("affiche valeur, précédente, prévision absente, période et source", () => {
    render(<InflationCard indicator={cpi} />);

    expect(screen.getByText("3,0 %")).toBeInTheDocument();
    expect(screen.getByText(/2,5 %/)).toBeInTheDocument();
    expect(within(screen.getByText("Prévision").parentElement!).getByText("—")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "FRED" })).toHaveAttribute("target", "_blank");
  });
});

describe("MacroPanel", () => {
  it("affiche les deux pays, « — » si pas de donnée et le calendrier coloré par impact", async () => {
    mockFetch({ "/api/macro": macro, "/api/calendar": calendar() });

    renderWithProviders(<MacroPanel pair={eurusd} />);

    expect(await screen.findByText("Zone euro")).toBeInTheDocument();
    expect(screen.getByText("Etats-Unis")).toBeInTheDocument();
    expect(screen.getByText(/après la prochaine mise à jour quotidienne/)).toBeInTheDocument();
    expect(await screen.findByText("CPI YoY")).toBeInTheDocument();
    expect(screen.getByText("Fort")).toHaveClass("text-rose-700");
    expect(screen.getByText("Faible")).toBeInTheDocument();
    expect(screen.getByText("Source : ForexFactory · heures locales")).toBeInTheDocument();
  });

  it("propose hier / aujourd'hui / demain", async () => {
    mockFetch({ "/api/macro": macro, "/api/calendar": calendar() });

    renderWithProviders(<MacroPanel pair={eurusd} />);

    for (const label of ["Hier", "Aujourd'hui", "Demain"]) {
      expect(await screen.findByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByRole("button", { name: "Aujourd'hui" })).toHaveAttribute("aria-pressed", "true");
  });

  it("indique « Source non configurée » sans clé Finnhub ni FRED", async () => {
    mockFetch({
      "/api/macro": {
        ...macro,
        sources: [{ name: "FRED", configured: false, message: "Source non configurée (FRED_API_KEY absente du .env)" }],
      },
      "/api/calendar": calendar({ events: [], source: { name: "Finnhub (calendrier)", configured: false, message: "Source non configurée" } }),
    });

    renderWithProviders(<MacroPanel pair={eurusd} />);

    expect(await screen.findByText("Source non configurée")).toBeInTheDocument();
    expect(await screen.findByText(/FRED : Source non configurée/)).toBeInTheDocument();
  });
});
