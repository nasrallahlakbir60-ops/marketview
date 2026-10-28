import { QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { RequireAuth } from "./components/auth/RequireAuth";
import { Footer } from "./components/layout/Footer";
import { ME_KEY } from "./hooks/useAuth";
import { AccountPage } from "./pages/AccountPage";
import { AuthPage } from "./pages/AuthPage";
import { Header } from "./components/layout/Header";
import { HomePage } from "./pages/HomePage";
import { MarketPage } from "./pages/MarketPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ApiError } from "./services/api";

const queryClient: QueryClient = new QueryClient({
  // Session expirée ou fermée ailleurs : une API répond 401, on repasse en "non connecté" (retour à /login).
  queryCache: new QueryCache({
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) {
        queryClient.setQueryData(ME_KEY, null);
      }
    },
  }),
  defaultOptions: {
    queries: {
      // Pas de nouvel essai sur une erreur client (404, 429...) : la réponse ne changera pas.
      retry: (failureCount, error) =>
        failureCount < 1 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex min-h-screen flex-col bg-surface">
          <Header />
          <div className="flex-1">
            <Routes>
              <Route element={<AuthPage mode="login" />} path="/login" />
              <Route element={<AuthPage mode="register" />} path="/register" />
              <Route element={<RequireAuth><HomePage /></RequireAuth>} path="/" />
              <Route element={<RequireAuth><MarketPage /></RequireAuth>} path="/market/:symbol" />
              <Route element={<RequireAuth><AccountPage /></RequireAuth>} path="/account" />
              <Route element={<NotFoundPage />} path="*" />
            </Routes>
          </div>
          <Footer />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
