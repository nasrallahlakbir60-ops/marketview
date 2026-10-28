import type {
  Activity,
  AuthConfig,
  CalendarResponse,
  MacroResponse,
  NewsItem,
  Pair,
  PairDetail,
  SourceStatus,
  User,
} from "../types";

// Vide en production : le frontend et l'API sont servis par le même domaine (Nginx).
export const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type QueryParams = Record<string, string | number | undefined>;

async function request<T>(method: string, path: string, params: QueryParams = {}, body?: unknown): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) query.set(key, String(value));
  }
  const url = `${API_URL}${path}${query.size ? `?${query}` : ""}`;

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      // Cookie de session httpOnly : envoyé aussi en dev, où l'API est sur un autre port.
      credentials: "include",
      headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Impossible de joindre le serveur MarketView. Vérifiez votre connexion.", 0);
  }

  if (!response.ok) {
    let detail = `Erreur du serveur (${response.status}).`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
      // Erreur de validation FastAPI : [{ msg: "Value error, ..." }]
      else if (Array.isArray(payload.detail) && typeof payload.detail[0]?.msg === "string") {
        detail = payload.detail[0].msg.replace(/^Value error, /, "");
      }
    } catch {
      // Corps non JSON : on garde le message générique.
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const apiGet = <T>(path: string, params?: QueryParams) => request<T>("GET", path, params);

export const api = {
  pairs: () => apiGet<Pair[]>("/api/pairs"),
  pair: (symbol: string) => apiGet<PairDetail>(`/api/pairs/${encodeURIComponent(symbol)}`),
  news: (pair: string, limit = 50) => apiGet<NewsItem[]>("/api/news", { pair, limit }),
  newsSources: () => apiGet<SourceStatus[]>("/api/news/sources"),
  macro: (pair: string) => apiGet<MacroResponse>("/api/macro", { pair }),
  calendar: (pair: string, day = "today") => apiGet<CalendarResponse>("/api/calendar", { pair, day }),
};

export const authApi = {
  config: () => apiGet<AuthConfig>("/api/auth/config"),
  me: () => apiGet<User>("/api/auth/me"),
  register: (data: { email: string; password: string; full_name: string }) =>
    request<User>("POST", "/api/auth/register", {}, data),
  login: (data: { email: string; password: string }) => request<User>("POST", "/api/auth/login", {}, data),
  google: (credential: string) => request<User>("POST", "/api/auth/google", {}, { credential }),
  logout: () => request<void>("POST", "/api/auth/logout"),
  logoutAll: () => request<void>("POST", "/api/auth/logout-all"),
  activity: () => apiGet<Activity[]>("/api/auth/me/activity"),
  exportData: () => apiGet<Record<string, unknown>>("/api/auth/me/export"),
  deleteAccount: () => request<void>("DELETE", "/api/auth/me"),
};
