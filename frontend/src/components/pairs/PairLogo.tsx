import { useState } from "react";

import type { Pair } from "../../types";

// Code pays (ISO 3166-1 alpha-2) des drapeaux servis par flagcdn.com.
const FLAGS: Record<string, string> = {
  USD: "us", EUR: "eu", GBP: "gb", JPY: "jp", CHF: "ch", AUD: "au", CAD: "ca", NZD: "nz",
  SGD: "sg", HKD: "hk", NOK: "no", SEK: "se", DKK: "dk", PLN: "pl", CZK: "cz", HUF: "hu",
  TRY: "tr", ZAR: "za", MXN: "mx", CNH: "cn", THB: "th", INR: "in", MAD: "ma",
  // Indices : drapeau du marché concerné.
  DXY: "us", US30: "us", SPX500: "us", NAS100: "us", GER40: "de", UK100: "gb", FRA40: "fr", JP225: "jp",
};

// Actifs sans drapeau : pastille colorée + symbole.
const BADGES: Record<string, { label: string; background: string; color: string }> = {
  XAU: { label: "Au", background: "linear-gradient(135deg,#fde68a,#d4a017 55%,#a16207)", color: "#422006" },
  XAG: { label: "Ag", background: "linear-gradient(135deg,#f8fafc,#cbd5e1 55%,#94a3b8)", color: "#1e293b" },
  XPT: { label: "Pt", background: "linear-gradient(135deg,#e5e7eb,#a8b0bd 55%,#6b7280)", color: "#111827" },
  XPD: { label: "Pd", background: "linear-gradient(135deg,#ede9fe,#b8b3c9 55%,#7c7891)", color: "#1f1b2e" },
  WTI: { label: "🛢", background: "linear-gradient(135deg,#3f3f46,#18181b)", color: "#fafafa" },
  BRENT: { label: "🛢", background: "linear-gradient(135deg,#334155,#0f172a)", color: "#fafafa" },
  NATGAS: { label: "🔥", background: "linear-gradient(135deg,#1d4ed8,#1e3a8a)", color: "#fafafa" },
  BTC: { label: "₿", background: "#f7931a", color: "#ffffff" },
  ETH: { label: "Ξ", background: "#627eea", color: "#ffffff" },
  SOL: { label: "◎", background: "linear-gradient(135deg,#9945ff,#14f195)", color: "#ffffff" },
  XRP: { label: "✕", background: "#23292f", color: "#ffffff" },
  BNB: { label: "◆", background: "#f3ba2f", color: "#1f1f1f" },
};

function AssetIcon({ code, className }: { code: string; className: string }) {
  const [failed, setFailed] = useState(false);
  const flag = FLAGS[code];
  const ring = `${className} overflow-hidden rounded-full ring-2 ring-panel`;

  if (flag && !failed) {
    return (
      <img
        alt=""
        className={`${ring} bg-line/10 object-cover`}
        draggable={false}
        loading="lazy"
        onError={() => setFailed(true)}
        src={`https://flagcdn.com/${flag}.svg`}
      />
    );
  }

  const badge = BADGES[code];
  return (
    <span
      className={`${ring} grid place-items-center font-bold leading-none`}
      style={badge ? { background: badge.background, color: badge.color } : undefined}
    >
      <span className={badge ? "text-[0.85em]" : "text-[0.5em] tracking-tight text-fg/80"}>
        {badge?.label ?? code.slice(0, 3)}
      </span>
    </span>
  );
}

interface PairLogoProps {
  pair: Pick<Pair, "base" | "quote" | "category">;
  size?: "md" | "lg";
}

export function PairLogo({ pair, size = "md" }: PairLogoProps) {
  const box = size === "lg" ? "h-14 w-14 text-xl" : "h-11 w-11 text-base";
  const icon = size === "lg" ? "h-10 w-10" : "h-8 w-8";

  // Indice : un seul logo (la devise de cotation n'apporte rien).
  if (pair.category === "index") {
    return (
      <span aria-hidden="true" className={`${box} grid shrink-0 place-items-center`}>
        <AssetIcon className={size === "lg" ? "h-12 w-12" : "h-10 w-10"} code={pair.base} />
      </span>
    );
  }

  return (
    <span aria-hidden="true" className={`${box} relative block shrink-0`}>
      <AssetIcon className={`${icon} absolute left-0 top-0`} code={pair.base} />
      <AssetIcon className={`${icon} absolute bottom-0 right-0`} code={pair.quote} />
    </span>
  );
}
