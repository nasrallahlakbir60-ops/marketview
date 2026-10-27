/** Nombre au format français ; "—" si la valeur n'est pas disponible (jamais de valeur inventée). */
export function formatNumber(value: number | null | undefined, maxDigits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("fr-FR", { minimumFractionDigits: 0, maximumFractionDigits: maxDigits });
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 2 })} %`;
}

export function formatWithUnit(value: number | null | undefined, unit: string | null): string {
  const formatted = formatNumber(value);
  if (formatted === "—" || !unit) return formatted;
  return unit === "%" ? `${formatted} %` : `${formatted} ${unit}`;
}
