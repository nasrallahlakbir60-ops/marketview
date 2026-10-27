import { describe, expect, it } from "vitest";

import { formatPeriod, formatRelative } from "./formatDate";
import { formatPercent, formatWithUnit } from "./formatNumber";

describe("formatRelative", () => {
  const now = Date.UTC(2026, 9, 27, 12, 0, 0);
  const ago = (ms: number) => new Date(now - ms).toISOString();

  it("affiche une heure relative en français", () => {
    expect(formatRelative(ago(20_000), now)).toBe("à l'instant");
    expect(formatRelative(ago(5 * 60_000), now)).toBe("il y a 5 min");
    expect(formatRelative(ago(3 * 3_600_000), now)).toBe("il y a 3 h");
    expect(formatRelative(ago(2 * 86_400_000), now)).toBe("il y a 2 j");
  });

  it("gère les dates invalides et futures", () => {
    expect(formatRelative("pas une date", now)).toBe("—");
    expect(formatRelative(new Date(now + 60_000).toISOString(), now)).toBe("à l'instant");
  });
});

describe("formatPeriod", () => {
  it("formate mois, année et jour", () => {
    expect(formatPeriod("2026-09")).toMatch(/sept\.? 2026/);
    expect(formatPeriod("2025")).toBe("2025");
    expect(formatPeriod("2026-10-15")).toMatch(/15 oct\.? 2026/);
    expect(formatPeriod(null)).toBe("—");
  });
});

describe("formatNumber", () => {
  it("n'invente jamais de valeur", () => {
    expect(formatPercent(null)).toBe("—");
    expect(formatWithUnit(null, "%")).toBe("—");
  });

  it("formate au format français", () => {
    expect(formatPercent(2.5)).toBe("2,5 %");
    expect(formatWithUnit(250, "K")).toBe("250 K");
  });
});
