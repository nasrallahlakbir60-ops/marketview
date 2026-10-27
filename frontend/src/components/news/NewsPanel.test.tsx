import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { eurusd, makeNews, mockFetch, renderWithProviders } from "../../test/utils";
import { NewsItem } from "./NewsItem";
import { NewsPanel } from "./NewsPanel";

const socketState = { status: "live" as const, newIds: new Set<number>() };
vi.mock("../../hooks/useNewsSocket", () => ({ useNewsSocket: () => socketState }));

describe("NewsItem", () => {
  it("affiche titre, source, heure relative et un lien vers un nouvel onglet", () => {
    render(
      <ul>
        <NewsItem labels={{ EUR: "EUR" }} news={makeNews()} now={Date.now()} />
      </ul>,
    );

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://example.com/ecb");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText("ECB keeps rates unchanged")).toBeInTheDocument();
    expect(screen.getByText("BCE")).toBeInTheDocument();
    expect(screen.getByText("il y a 5 min")).toBeInTheDocument();
  });
});

describe("NewsPanel", () => {
  beforeEach(() => {
    socketState.newIds = new Set();
  });

  it("affiche les news, l'indicateur En direct et filtre par devise", async () => {
    mockFetch({
      "/api/news": [
        makeNews({ id: 1, title: "Fed cuts rates", currencies: ["USD"] }),
        makeNews({ id: 2, title: "ECB holds", currencies: ["EUR"] }),
      ],
      "/api/news/sources": [{ name: "Finnhub", configured: false, message: "Source non configurée" }],
    });

    renderWithProviders(<NewsPanel pair={eurusd} />);

    expect(await screen.findByText("Fed cuts rates")).toBeInTheDocument();
    expect(screen.getByText("En direct")).toBeInTheDocument();
    expect(await screen.findByText("Finnhub : Source non configurée")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "EUR" }));
    expect(screen.queryByText("Fed cuts rates")).not.toBeInTheDocument();
    expect(screen.getByText("ECB holds")).toBeInTheDocument();
  });

  it("affiche un état vide propre", async () => {
    mockFetch({ "/api/news": [], "/api/news/sources": [] });

    renderWithProviders(<NewsPanel pair={eurusd} />);

    expect(await screen.findByText("Aucune news pour le moment")).toBeInTheDocument();
  });

  it("affiche l'erreur du serveur avec un bouton Réessayer", async () => {
    mockFetch({ "/api/news": { status: 500, body: { detail: "Base indisponible" } }, "/api/news/sources": [] });

    renderWithProviders(<NewsPanel pair={eurusd} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Base indisponible");
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });
});
