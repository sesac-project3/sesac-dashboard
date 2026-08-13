"use client";

import {
  CategoryScale,
  Chart as ChartJS,
  LineElement,
  LinearScale,
  PointElement,
  type Plugin,
  Tooltip,
  type TooltipModel,
} from "chart.js";
import { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";

import type { Candle, CandleInterval } from "@/entities/stock/chart-types";
import { getStockCandles } from "@/shared/api/stocks";

ChartJS.register(CategoryScale, LineElement, LinearScale, PointElement, Tooltip);

interface StockChartProps {
  stockCode: string;
  interval?: CandleInterval;
}

const formatPrice = (value: number) => value.toLocaleString("ko-KR");

const formatTooltipTimestamp = (timestamp: string, interval: CandleInterval) => {
  const date = new Date(timestamp.includes("T") ? timestamp : `${timestamp}T00:00:00`);
  if (Number.isNaN(date.getTime())) return timestamp;

  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  if (interval === "MONTHLY") return `${date.getFullYear()}.${month}.`;
  if (interval === "MINUTE_15") {
    return `${month}.${day}. ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  }
  if (interval === "DAILY") {
    return `${date.getFullYear()}.${month}.${day}.(${"일월화수목금토"[date.getDay()]})`;
  }
  return `${date.getFullYear()}.${month}.${day}.`;
};

const createExtremaLabelsPlugin = (candles: Candle[]): Plugin<"line"> => ({
  id: "extremaLabels",
  afterDatasetsDraw: (chart) => {
    const dataset = chart.getDatasetMeta(0);
    const closePrices = chart.data.datasets[0]?.data as number[];
    if (!dataset.data.length || !closePrices.length) return;

    const maxIndex = closePrices.indexOf(Math.max(...closePrices));
    const minIndex = closePrices.indexOf(Math.min(...closePrices));
    const context = chart.ctx;

    context.save();
    context.fillStyle = "#542be9";
    context.font = "12px Pretendard, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";

    for (const { index, label, offset } of [
      { index: maxIndex, label: `고가 ${formatPrice(candles[maxIndex]?.highPrice ?? 0)}`, offset: -14 },
      { index: minIndex, label: `저가 ${formatPrice(candles[minIndex]?.lowPrice ?? 0)}`, offset: 14 },
    ]) {
      const point = dataset.data[index];
      if (!point) continue;
      const halfWidth = context.measureText(label).width / 2;
      const x = Math.min(
        Math.max(point.x, chart.chartArea.left + halfWidth),
        chart.chartArea.right - halfWidth,
      );
      context.fillText(label, x, point.y + offset);
    }

    context.restore();
  },
});

export default function StockChart({
  stockCode,
  interval = "DAILY",
}: StockChartProps) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getStockCandles(stockCode, interval)
      .then((response) => {
        if (!cancelled) {
          setCandles(response?.candles ?? []);
          setError(false);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCandles([]);
          setError(true);
          setIsLoading(false);
        }
      })

    return () => {
      cancelled = true;
    };
  }, [stockCode, interval]);

  if (isLoading) {
    return <div className="flex h-72 items-center justify-center text-sm text-caption">차트를 불러오는 중...</div>;
  }

  if (error) {
    return <div className="flex h-72 items-center justify-center text-sm text-danger">차트를 불러오지 못했어요.</div>;
  }

  if (candles.length === 0) {
    return <div className="flex h-72 items-center justify-center text-sm text-caption">표시할 데이터가 없어요.</div>;
  }

  const closePrices = candles.map((candle) => candle.closePrice);
  const maxClose = Math.max(...closePrices);
  const minClose = Math.min(...closePrices);
  const extremaLabelsPlugin = createExtremaLabelsPlugin(candles);
  const externalTooltip = ({
    chart,
    tooltip,
  }: {
    chart: ChartJS;
    tooltip: TooltipModel<"line">;
  }) => {
    let element = chart.canvas.parentNode?.querySelector(".chart-tooltip") as HTMLDivElement | null;
    if (!element) {
      element = document.createElement("div");
      element.className = "chart-tooltip";
      element.style.cssText =
        "position:absolute;transform:translate(12px,-50%);padding:12px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;box-shadow:0 4px 12px rgba(17,24,39,.08);pointer-events:none;white-space:nowrap;transition:opacity .1s";
      chart.canvas.parentNode?.appendChild(element);
    }

    if (tooltip.opacity === 0) {
      element.style.opacity = "0";
      return;
    }

    const candle = candles[tooltip.dataPoints[0]?.dataIndex];
    if (!candle) return;

    element.replaceChildren();
    const title = document.createElement("div");
    title.textContent = formatTooltipTimestamp(String(tooltip.title[0] ?? ""), interval);
    title.style.cssText = "color:#374151;font-weight:700;margin-bottom:8px";
    element.appendChild(title);

    for (const [label, value, color] of [
      ["시가", candle.openPrice, "#111827"],
      ["고가", candle.highPrice, "#ef4444"],
      ["저가", candle.lowPrice, "#3b82f6"],
      ["종가", candle.closePrice, "#111827"],
      ["거래량", candle.volume, "#9ca3af"],
    ] as const) {
      const row = document.createElement("div");
      row.style.cssText = "display:flex;justify-content:space-between;gap:20px;font-family:monospace";
      row.style.color = color;
      row.innerHTML = `<span>${label}</span><span>${formatPrice(value)}</span>`;
      element.appendChild(row);
    }

    element.style.opacity = "1";
    element.style.left = `${tooltip.caretX}px`;
    element.style.top = `${tooltip.caretY}px`;
  };
  const data = {
    labels: candles.map((candle) => candle.timestamp),
    datasets: [
      {
        label: "종가",
        data: candles.map((candle) => candle.closePrice),
        borderColor: "#542be9",
        borderWidth: 2,
        pointRadius: (context: { dataIndex: number }) =>
          closePrices[context.dataIndex] === maxClose || closePrices[context.dataIndex] === minClose ? 3 : 0,
        pointBackgroundColor: "#542be9",
        pointBorderColor: "#542be9",
        pointBorderWidth: 0,
        pointHitRadius: 12,
        tension: 0.25,
        fill: false,
      },
    ],
  };

  return (
    <div className="relative h-72 w-full">
      <Line
        data={data}
        plugins={[extremaLabelsPlugin]}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          layout: { padding: { top: 20, bottom: 20 } },
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: {
              enabled: false,
              external: externalTooltip,
            },
          },
          scales: {
            x: { display: false },
            y: { display: false },
          },
        }}
      />
    </div>
  );
}
