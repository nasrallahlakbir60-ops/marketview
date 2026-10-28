import { fireEvent, screen, waitFor } from "@testing-library/react";
import { Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RequireAuth } from "../components/auth/RequireAuth";
import { mockFetch, renderWithProviders } from "../test/utils";
import type { User } from "../types";
import { AuthPage } from "./AuthPage";

const user: User = {
  id: 1,
  email: "trader@example.com",
  full_name: "Test Trader",
  avatar_url: null,
  has_password: true,
  google_linked: false,
  created_at: "2026-10-28T10:00:00Z",
  last_login_at: "2026-10-28T10:00:00Z",
};

function CurrentPath() {
  const location = useLocation();
  return <p data-testid="path">{`${location.pathname}${location.search}`}</p>;
}

function renderApp(route: string) {
  return renderWithProviders(
    <>
      <Routes>
        <Route element={<AuthPage mode="login" />} path="/login" />
        <Route element={<AuthPage mode="register" />} path="/register" />
        <Route element={<RequireAuth><p>Page marché</p></RequireAuth>} path="/market/:symbol" />
        <Route element={<RequireAuth><p>Accueil</p></RequireAuth>} path="/" />
      </Routes>
      <CurrentPath />
    </>,
    { route },
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("Accès réservé", () => {
  it("renvoie un visiteur non connecté vers /login en mémorisant la page demandée", async () => {
    mockFetch({ "/api/auth/me": { status: 401, body: { detail: "Connexion requise." } }, "/api/auth/config": { google_client_id: null } });

    renderApp("/market/EURUSD");

    expect(await screen.findByRole("heading", { name: "Bon retour parmi nous" })).toBeInTheDocument();
    expect(screen.getByTestId("path")).toHaveTextContent("/login?next=%2Fmarket%2FEURUSD");
    expect(screen.queryByText("Page marché")).not.toBeInTheDocument();
  });

  it("affiche la page à un utilisateur connecté", async () => {
    mockFetch({ "/api/auth/me": user });

    renderApp("/market/EURUSD");

    expect(await screen.findByText("Page marché")).toBeInTheDocument();
  });
});

describe("AuthPage", () => {
  it("connecte puis renvoie vers la page demandée", async () => {
    const fetchMock = mockFetch({
      "/api/auth/me": { status: 401 },
      "/api/auth/config": { google_client_id: null },
      "/api/auth/login": user,
    });

    renderApp("/login?next=%2Fmarket%2FEURUSD");

    fireEvent.change(await screen.findByLabelText("Adresse e-mail"), { target: { value: "trader@example.com" } });
    fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: "motdepasse1" } });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    expect(await screen.findByText("Page marché")).toBeInTheDocument();
    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).includes("/api/auth/login"))!;
    expect(init).toMatchObject({ method: "POST", credentials: "include" });
    expect(JSON.parse(String(init?.body))).toEqual({ email: "trader@example.com", password: "motdepasse1" });
  });

  it("affiche l'erreur renvoyée par le serveur", async () => {
    mockFetch({
      "/api/auth/me": { status: 401 },
      "/api/auth/config": { google_client_id: null },
      "/api/auth/register": {
        status: 422,
        body: { detail: [{ msg: "Value error, Le mot de passe doit contenir au moins 8 caractères, dont une lettre et un chiffre." }] },
      },
    });

    renderApp("/register");

    fireEvent.change(await screen.findByLabelText("Nom"), { target: { value: "Test" } });
    fireEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/^Le mot de passe doit contenir au moins 8 caractères/);
  });

  it("n'affiche le bouton Google que s'il est configuré", async () => {
    mockFetch({ "/api/auth/me": { status: 401 }, "/api/auth/config": { google_client_id: null } });

    renderApp("/login");

    await screen.findByRole("heading", { name: "Bon retour parmi nous" });
    await waitFor(() => expect(screen.queryByText("ou par e-mail")).not.toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Créer un compte" })).toHaveAttribute("href", "/register");
  });
});
