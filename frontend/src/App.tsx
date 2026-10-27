import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Footer } from "./components/layout/Footer";
import { Header } from "./components/layout/Header";
import { HomePage } from "./pages/HomePage";
import { MarketPage } from "./pages/MarketPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ApiError } from "./services/api";

const queryClient = new QueryClient({
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
              <Route element={<HomePage />} path="/" />
              <Route element={<MarketPage />} path="/market/:symbol" />
              <Route element={<NotFoundPage />} path="*" />
            </Routes>
          </div>
          <Footer />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
