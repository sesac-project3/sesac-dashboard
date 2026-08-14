"use client";

import { useEffect, useState } from "react";
import type { Candle, CandleInterval, Quote } from "@/entities/stock/chart-types";
import { useStockWebSocketContext } from "./StockWebSocketProvider";

export default function useStockSubscription(stockCode: string) {
  const { connectionState, subscribe } = useStockWebSocketContext();
  const [quote, setQuote] = useState<Quote | null>(null);
  const [candlesByInterval, setCandlesByInterval] = useState<Partial<Record<CandleInterval, Candle>>>({});

  useEffect(() => {
    if (!stockCode) return;
    return subscribe(stockCode, (message) => {
      if (message.type === "quote_update" || message.type === "quote_snapshot") {
        setQuote(message);
        return;
      }
      if (message.type !== "candle_snapshot" && message.type !== "candle_update") return;
      setCandlesByInterval((previous) => ({ ...previous, [message.interval]: message.candle }));
    });
  }, [stockCode, subscribe]);

  return { connectionState, quote, candlesByInterval };
}
