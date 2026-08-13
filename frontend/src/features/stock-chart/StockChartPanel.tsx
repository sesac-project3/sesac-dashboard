"use client";

import { useState } from "react";

import type { Candle, CandleInterval } from "@/entities/stock/chart-types";
import ChartRangeTabs, { CHART_TABS } from "@/features/stock-chart/ChartRangeTabs";
import StockChart from "@/features/stock-chart/StockChart";

export default function StockChartPanel({
  stockCode,
  candlesByInterval,
}: {
  stockCode: string;
  candlesByInterval: Partial<Record<CandleInterval, Candle>>;
}) {
  const [selected, setSelected] = useState(0);
  const interval = CHART_TABS[selected].interval ?? "MONTHLY";

  return (
    <div className="flex flex-col">
      <div className="flex flex-col px-4">
        <div className="flex flex-col border-t border-border-soft pt-4 pb-4">
          <ChartRangeTabs selected={selected} onSelect={setSelected} />
        </div>
      </div>
      <div className="flex flex-col px-4">
        <div className="flex flex-col pt-4 pb-4">
          <StockChart
            key={interval}
            stockCode={stockCode}
            interval={interval}
            realtimeCandle={candlesByInterval[interval]}
          />
        </div>
      </div>
    </div>
  );
}
