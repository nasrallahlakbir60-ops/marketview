const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** Heure relative en français : "à l'instant", "il y a 5 min", "il y a 3 h", "il y a 2 j", puis la date. */
export function formatRelative(value: string | Date, now: number = Date.now()): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const time = date.getTime();
  if (Number.isNaN(time)) return "—";
  const diff = Math.max(0, now - time);
  if (diff < MINUTE) return "à l'instant";
  if (diff < HOUR) return `il y a ${Math.floor(diff / MINUTE)} min`;
  if (diff < DAY) return `il y a ${Math.floor(diff / HOUR)} h`;
  if (diff < 7 * DAY) return `il y a ${Math.floor(diff / DAY)} j`;
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}

export function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/** "2026-09" -> "sept. 2026", "2025" -> "2025", "2026-10-15" -> "15 oct. 2026". */
export function formatPeriod(period: string | null): string {
  if (!period) return "—";
  const month = /^(\d{4})-(\d{2})$/.exec(period);
  if (month) {
    return new Date(Date.UTC(Number(month[1]), Number(month[2]) - 1, 1)).toLocaleDateString("fr-FR", {
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(period)) {
    return new Date(`${period}T00:00:00Z`).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  }
  return period;
}
