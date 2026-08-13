import base, { type ApiEnvelope } from "@/shared/api/base";
import type { MarketIndex, Stock } from "@/entities/stock/types";
import type { CandleInterval, CandleResponse } from "@/entities/stock/chart-types";

export const getMarketIndices = () =>
  base
    .get<ApiEnvelope<MarketIndex[]>>("/stocks/market/indices")
    .then((res) => res.data.data ?? []);

export const getStocks = () =>
  base.get<ApiEnvelope<Stock[]>>("/stocks").then((res) => res.data.data ?? []);

export const getStockCandles = (stockCode: string, interval: CandleInterval) =>
  base
    .get<ApiEnvelope<CandleResponse>>(`/stocks/${stockCode}/candles`, {
      params: { interval },
    })
    .then((res) => res.data.data);
