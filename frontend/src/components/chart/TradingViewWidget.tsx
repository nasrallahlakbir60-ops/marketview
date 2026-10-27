import { useEffect, useRef } from "react";

import { useThemeStore } from "../../store/themeStore";
import type { Timeframe } from "../../types";

interface TradingViewWidgetProps {
  symbol: string;
  timeframe: Timeframe;
}

const colors = {
  dark: { backgroundColor: "rgba(16, 23, 19, 1)", gridColor: "rgba(255, 255, 255, 0.05)" },
  light: { backgroundColor: "rgba(255, 255, 255, 1)", gridColor: "rgba(15, 23, 42, 0.06)" },
};

export function TradingViewWidget({ symbol, timeframe }: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const theme = useThemeStore((state) => state.theme);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const timer = window.setTimeout(() => {
      const widget = document.createElement("div");
      widget.className = "tradingview-widget-container__widget h-full w-full";
      const script = document.createElement("script");
      script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
      script.async = true;
      script.type = "text/javascript";
      script.textContent = JSON.stringify({
        autosize: true,
        symbol,
        interval: timeframe,
        timezone: "Etc/UTC",
        theme,
        style: "1",
        locale: "fr",
        ...colors[theme],
        hide_top_toolbar: false,
        hide_legend: false,
        allow_symbol_change: false,
        save_image: false,
        calendar: false,
        support_host: "https://www.tradingview.com",
      });
      container.append(widget, script);
    }, 0);

    return () => {
      window.clearTimeout(timer);
      container.replaceChildren();
    };
  }, [symbol, timeframe, theme]);

  return (
    <div className="h-[420px] w-full sm:h-[520px] xl:h-[min(68vh,720px)]">
      <div
        aria-label={`Graphique TradingView ${symbol}`}
        className="tradingview-widget-container relative h-full w-full overflow-hidden rounded-xl"
        ref={containerRef}
      />
    </div>
  );
}
