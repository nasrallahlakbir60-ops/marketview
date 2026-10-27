import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { createReconnectingSocket, wsUrl, type SocketStatus } from "../services/socket";
import type { NewsItem } from "../types";
import { NEWS_LIMIT, newsQueryKey } from "./useNews";

type ServerMessage =
  | { type: "status"; live: boolean }
  | { type: "news"; data: NewsItem }
  | { type: "ping" };

/** Reçoit les news en direct et les ajoute en haut de la liste (cache React Query). */
export function useNewsSocket(symbol: string) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const [newIds, setNewIds] = useState<ReadonlySet<number>>(() => new Set());

  useEffect(() => {
    setNewIds(new Set());
    const key = newsQueryKey(symbol);
    return createReconnectingSocket({
      url: wsUrl(`/ws/news/${encodeURIComponent(symbol)}`),
      onStatus: (next) => {
        // "live" n'est confirmé que par le message de statut du serveur.
        if (next !== "live") setStatus(next);
      },
      onReconnect: () => void queryClient.invalidateQueries({ queryKey: key }),
      onMessage: (raw) => {
        const message = raw as ServerMessage;
        if (message.type === "status") {
          setStatus(message.live ? "live" : "offline");
        } else if (message.type === "news") {
          const news = message.data;
          // Si la liste n'est pas encore chargée, le chargement initial inclura cette news.
          queryClient.setQueryData<NewsItem[]>(key, (current) =>
            !current || current.some((item) => item.id === news.id)
              ? current
              : [news, ...current].slice(0, NEWS_LIMIT),
          );
          setNewIds((current) => new Set(current).add(news.id));
        }
      },
    });
  }, [symbol, queryClient]);

  return { status, newIds };
}
