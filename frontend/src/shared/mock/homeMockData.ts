export interface ExchangeRateMock {
  currency: string;
  value: string;
  changePercent: string;
  isUp: boolean;
}

export const MOCK_EXCHANGE_RATES: ExchangeRateMock[] = [
  { currency: "원/엔", value: "888.90", changePercent: "0.33%", isUp: true },
  { currency: "원/유로", value: "1,634.35", changePercent: "0.33%", isUp: true },
  { currency: "원/달러", value: "1,385.20", changePercent: "0.15%", isUp: false },
];
