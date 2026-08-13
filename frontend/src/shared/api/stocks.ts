import base, { type ApiEnvelope } from "@/shared/api/base";
import type { MarketIndex, Stock } from "@/entities/stock/types";

export interface DailySentimentItem {
  date: string;
  day: string;
  sentiment: string;
  emoji: string;
}

export interface WeeklySentimentResponse {
  stockId: number;
  weeklySentiments: DailySentimentItem[];
}

export const getMarketIndices = () =>
  base
    .get<ApiEnvelope<MarketIndex[]>>("/stocks/market/indices")
    .then((res) => res.data.data ?? []);

export const getStocks = () =>
  base.get<ApiEnvelope<Stock[]>>("/stocks").then((res) => res.data.data ?? []);

export const getWeeklyStockSentiments = (stockCodeOrId: string) =>
  base
    .get<ApiEnvelope<WeeklySentimentResponse>>(`/stocks/${stockCodeOrId}/sentiments/weekly`)
    .then((res) => res.data.data);

