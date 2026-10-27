export interface Pair {
  symbol: string;
  name: string;
  category: string;
  base: string;
  quote: string;
  tradingview_symbol: string;
  active: boolean;
}

export interface NewsTag {
  code: string;
  label: string;
}

export interface Country {
  code: string;
  name: string;
  currency: string;
}

export interface PairDetail extends Pair {
  news_tags: NewsTag[];
  macro_countries: Country[];
}

export interface NewsItem {
  id: number;
  title: string;
  summary: string | null;
  url: string;
  source: string;
  image_url: string | null;
  published_at: string;
  currencies: string[];
}

export interface MacroIndicator {
  country: string;
  indicator: string;
  label: string;
  value: number | null;
  previous: number | null;
  forecast: number | null;
  period: string | null;
  previous_period: string | null;
  frequency: string | null;
  release_date: string | null;
  source: string;
  source_url: string | null;
}

export interface SourceStatus {
  name: string;
  configured: boolean;
  message: string | null;
}

export interface MacroCountry extends Country {
  indicators: MacroIndicator[];
}

export interface MacroResponse {
  pair: string;
  countries: MacroCountry[];
  sources: SourceStatus[];
}

export type Impact = "low" | "medium" | "high";

export interface EconomicEvent {
  country: string;
  currency: string | null;
  event_name: string;
  impact: Impact;
  actual: number | null;
  forecast: number | null;
  previous: number | null;
  unit: string | null;
  event_time: string;
}

export interface CalendarResponse {
  pair: string;
  day: string;
  currencies: string[];
  events: EconomicEvent[];
  source: SourceStatus;
}

export type Timeframe = "1" | "5" | "15" | "60" | "240" | "D";

export interface TimeframeOption {
  label: string;
  value: Timeframe;
}
