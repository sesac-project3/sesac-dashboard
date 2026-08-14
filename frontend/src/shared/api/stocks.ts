import base, { unwrapApiResponse, type ApiEnvelope } from "@/shared/api/base";
import type { HomeDashboard, MarketIndex, Stock } from "@/entities/stock/types";
import type { CandleInterval, CandleResponse } from "@/entities/stock/chart-types";

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

export const getHomeDashboard = () =>
  base
    .get<ApiEnvelope<HomeDashboard>>("/stocks/home-dashboard")
    .then(unwrapApiResponse);

export const getStock = (stockCode: string) =>
  base.get<ApiEnvelope<Stock>>(`/stocks/${stockCode}`).then(unwrapApiResponse);

export const getWeeklyStockSentiments = (stockCodeOrId: string) =>
  base
    .get<ApiEnvelope<WeeklySentimentResponse>>(`/stocks/${stockCodeOrId}/sentiments/weekly`)
    .then(unwrapApiResponse);

export const getStockCandles = (stockCode: string, interval: CandleInterval) =>
  base
    .get<ApiEnvelope<CandleResponse>>(`/stocks/${stockCode}/candles`, {
      params: { interval },
    })
    .then(unwrapApiResponse);
