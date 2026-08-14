"use client";

import Card from "@/shared/ui/Card";
import StockChartPanel from "@/features/stock-chart/StockChartPanel";
import StockQuoteCard from "@/features/stock-quote/StockQuoteCard";
import type { Candle, CandleInterval, Quote } from "@/entities/stock/chart-types";

export default function StockLiveSection({
  stockCode,
  stockName,
  market,
  quote,
  candlesByInterval,
}: {
  stockCode: string;
  stockName: string;
  market: string;
  quote: Quote | null;
  candlesByInterval: Partial<Record<CandleInterval, Candle>>;
}) {
  return (
    <Card className="flex flex-col border-0 px-0 py-0 shadow-none">
      <StockQuoteCard
        stockCode={stockCode}
        stockName={stockName}
        market={market}
        exchange="KRX"
        quote={quote}
      />
      <StockChartPanel stockCode={stockCode} candlesByInterval={candlesByInterval} />
    </Card>
  );
}
