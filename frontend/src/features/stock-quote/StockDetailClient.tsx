"use client";

import useStockWebSocket from "@/features/stock-chart/useStockWebSocket";
import StockLiveSection from "@/features/stock-quote/StockLiveSection";
import StockReportSummaryWidget from "@/features/report/StockReportSummaryWidget";
import WeeklySentimentWeather from "@/widgets/stock-weather/WeeklySentimentWeather";
import type { StockReport } from "@/entities/report/types";

// 시세 웹소켓을 이 컴포넌트에서 한 번만 열어서 StockLiveSection(현재가 카드)과
// StockReportSummaryWidget(AI 리포트 "1. 투자 판단 요약"의 현재가)이 같은 실시간
// quote.currentPrice를 공유한다 — 안 그러면 리포트 쪽은 생성 시점의 stale한
// report.currentPrice를 계속 보여주게 된다.
export default function StockDetailClient({
  stockCode,
  stockName,
  market,
  report,
}: {
  stockCode: string;
  stockName: string;
  market: string;
  report: StockReport | null;
}) {
  const { quote, candlesByInterval } = useStockWebSocket(stockCode);

  return (
    <>
      <StockLiveSection
        stockCode={stockCode}
        stockName={stockName}
        market={market}
        quote={quote}
        candlesByInterval={candlesByInterval}
      />

      <WeeklySentimentWeather stockCode={stockCode} />

      <div>
        <StockReportSummaryWidget
          report={report}
          stockName={stockName}
          stockCode={stockCode}
          livePrice={quote?.currentPrice}
        />
      </div>
    </>
  );
}
