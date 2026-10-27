import { API_URL } from "./api";

/** URL WebSocket : VITE_WS_URL, sinon dérivée de VITE_API_URL, sinon du domaine courant (production derrière Nginx). */
export function wsUrl(path: string): string {
  const explicit = (import.meta.env.VITE_WS_URL ?? "").replace(/\/$/, "");
  if (explicit) return `${explicit}${path}`;
  if (API_URL) return `${API_URL.replace(/^http/, "ws")}${path}`;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}

export type SocketStatus = "connecting" | "live" | "offline" | "polling";

export const liveUpdatesEnabled = import.meta.env.VITE_ENABLE_WS !== "false";

interface ReconnectingSocketOptions {
  url: string;
  onMessage: (data: unknown) => void;
  onStatus: (status: SocketStatus) => void;
  /** Appelé après une reconnexion réussie (pour récupérer ce qui a été manqué). */
  onReconnect?: () => void;
  minDelayMs?: number;
  maxDelayMs?: number;
}

/** WebSocket qui se reconnecte automatiquement (backoff exponentiel plafonné). */
export function createReconnectingSocket({
  url,
  onMessage,
  onStatus,
  onReconnect,
  minDelayMs = 1_000,
  maxDelayMs = 30_000,
}: ReconnectingSocketOptions): () => void {
  let socket: WebSocket | null = null;
  let timer: number | undefined;
  let attempts = 0;
  let closed = false;
  let hasConnected = false;

  const scheduleReconnect = () => {
    if (closed) return;
    const delay = Math.min(maxDelayMs, minDelayMs * 2 ** attempts);
    attempts += 1;
    timer = window.setTimeout(connect, delay);
  };

  function connect() {
    if (closed) return;
    onStatus("connecting");
    socket = new WebSocket(url);
    socket.onopen = () => {
      attempts = 0;
      if (hasConnected) onReconnect?.();
      hasConnected = true;
    };
    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(String(event.data)));
      } catch {
        // Message illisible : ignoré.
      }
    };
    socket.onclose = (event) => {
      socket = null;
      onStatus("offline");
      // 4404 : marché inconnu, inutile de réessayer.
      if (event.code !== 4404) scheduleReconnect();
    };
    socket.onerror = () => socket?.close();
  }

  const handleOnline = () => {
    if (!socket && !closed) {
      window.clearTimeout(timer);
      attempts = 0;
      connect();
    }
  };
  window.addEventListener("online", handleOnline);
  connect();

  return () => {
    closed = true;
    window.clearTimeout(timer);
    window.removeEventListener("online", handleOnline);
    if (socket) {
      socket.onclose = null;
      socket.close();
    }
  };
}
