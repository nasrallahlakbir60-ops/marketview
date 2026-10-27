import type { SocketStatus } from "../../services/socket";

const labels: Record<SocketStatus, string> = {
  live: "En direct",
  connecting: "Connexion...",
  offline: "Hors ligne, reconnexion...",
  polling: "Actualisation automatique toutes les 60 s",
};

export function LiveIndicator({ status }: { status: SocketStatus }) {
  return (
    <span aria-live="polite" className="inline-flex items-center gap-1.5 text-[11px] text-muted" title={labels[status]}>
      <span className="relative flex h-2 w-2" aria-hidden="true">
        {status === "live" && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />}
        <span
          className={`relative inline-flex h-2 w-2 rounded-full ${
            status === "live" ? "bg-emerald-400" : status === "connecting" ? "bg-amber-400" : status === "polling" ? "bg-accent" : "bg-faint"
          }`}
        />
      </span>
      {status === "offline" ? "Hors ligne" : status === "polling" ? "Auto 60 s" : labels[status]}
    </span>
  );
}
