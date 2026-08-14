export interface Stock {
  id: number;
  code: string;
  name: string;
  market: "KOSPI" | "KOSDAQ";
}

export interface MarketIndex {
  indexType: "KOSPI" | "KOSDAQ" | "USD_KRW";
  value: number;
  recordedAt: string;
}

export interface InvestorTrend {
  personal: number;
  foreign: number;
  institution: number;
}

export interface MarketIndexDetail {
  indexType: "KOSPI" | "KOSDAQ";
  title: string;
  value: number;
  change: number;
  changePercent: number;
  isUp: boolean;
  investors: InvestorTrend;
}

export interface StockRankingItem {
  code: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  isUp: boolean;
  volume: number;
  tradingValue: number;
}

export type RankingType = "상승률" | "하락률" | "거래대금" | "거래량";

export interface HomeDashboard {
  indices: MarketIndexDetail[];
  rankings: Record<RankingType, StockRankingItem[]>;
  asOf: string;
}

export interface MarketIssue {
  title: string;
  text: string;
  updatedAt: string;
}
