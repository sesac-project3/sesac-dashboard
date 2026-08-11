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
