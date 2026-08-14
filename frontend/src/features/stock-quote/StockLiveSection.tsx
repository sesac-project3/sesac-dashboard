"use client";

import Card from "@/shared/ui/Card";
import StockChartPanel from "@/features/stock-chart/StockChartPanel";
import useStockSubscription from "@/features/stock-chart/useStockSubscription";
import StockQuoteCard from "@/features/stock-quote/StockQuoteCard";

export default function StockLiveSection({
  stockCode,
  stockName,
  market,
}: {
  stockCode: string;
  stockName: string;
  market: string;
}) {
  const { quote, candlesByInterval } = useStockSubscription(stockCode);

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
