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
import { useEffect, useRef, useState } from "react";
import { Line } from "react-chartjs-2";

import type { Candle, CandleInterval } from "@/entities/stock/chart-types";
import { getStockCandles } from "@/shared/api/stocks";

ChartJS.register(CategoryScale, LineElement, LinearScale, PointElement, Tooltip);

interface StockChartProps {
  stockCode: string;
  interval?: CandleInterval;
  realtimeCandle?: Candle;
}

const formatPrice = (value: number) => value.toLocaleString("ko-KR");
const formatVolume = (value: number) => {
  if (value > 1_000_000) return `${Math.floor(value / 1_000).toLocaleString("ko-KR")}K`;
  return value.toLocaleString("ko-KR");
};

const applyRealtimeCandle = (candles: Candle[], realtimeCandle: Candle) => {
  if (!candles.length) return [realtimeCandle];

  const lastIndex = candles.length - 1;
  const lastTimestamp = Date.parse(candles[lastIndex].timestamp);
  const realtimeTimestamp = Date.parse(realtimeCandle.timestamp);
  const isSameTimestamp =
    Number.isNaN(lastTimestamp) || Number.isNaN(realtimeTimestamp)
      ? candles[lastIndex].timestamp === realtimeCandle.timestamp
      : lastTimestamp === realtimeTimestamp;

  return isSameTimestamp
    ? [...candles.slice(0, lastIndex), realtimeCandle]
    : [...candles, realtimeCandle];
};

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

const createExtremaLabelsPlugin = (candles: Candle[], primaryColor: string): Plugin<"line"> => ({
  id: "extremaLabels",
  afterDatasetsDraw: (chart) => {
    const dataset = chart.getDatasetMeta(0);
    const closePrices = chart.data.datasets[0]?.data as number[];
    if (!dataset.data.length || !closePrices.length) return;

    const maxIndex = closePrices.lastIndexOf(Math.max(...closePrices));
    const minIndex = closePrices.lastIndexOf(Math.min(...closePrices));
    const context = chart.ctx;

    context.save();
    context.fillStyle = primaryColor;
    context.font = "12px Pretendard, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";

    for (const { index, label, offset } of [
      { index: maxIndex, label: `고가 ${formatPrice(candles[maxIndex]?.highPrice ?? 0)}`, offset: -26 },
      { index: minIndex, label: `저가 ${formatPrice(candles[minIndex]?.lowPrice ?? 0)}`, offset: 26 },
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
  realtimeCandle,
}: StockChartProps) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const realtimeCandleRef = useRef<Candle | undefined>(realtimeCandle);

  useEffect(() => {
    realtimeCandleRef.current = realtimeCandle;
  }, [realtimeCandle]);

  useEffect(() => {
    let cancelled = false;

    getStockCandles(stockCode, interval)
      .then((response) => {
        if (!cancelled) {
          const nextCandles = response?.candles ?? [];
          const snapshot = realtimeCandleRef.current;
          setCandles(snapshot ? applyRealtimeCandle(nextCandles, snapshot) : nextCandles);
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

  useEffect(() => {
    if (!realtimeCandle) return;
    setCandles((previous) => applyRealtimeCandle(previous, realtimeCandle));
  }, [realtimeCandle]);

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
  const maxIndex = closePrices.lastIndexOf(maxClose);
  const minIndex = closePrices.lastIndexOf(minClose);
  const cssColor = (name: string, fallback: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  const primaryColor = cssColor("--color-primary", "#542be9");
  const neutral950 = cssColor("--color-neutral-950", "#191f28");
  const neutral300 = cssColor("--color-neutral-300", "#b0b8c1");
  const neutral800 = cssColor("--color-neutral-800", "#333d4b");
  const neutral200 = cssColor("--color-neutral-200", "#e5e8eb");
  const marketUp = cssColor("--color-market-up", "#ef4444");
  const marketDown = cssColor("--color-market-down", "#3b82f6");
  const extremaLabelsPlugin = createExtremaLabelsPlugin(candles, primaryColor);
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
        `position:absolute;transform:translate(12px,-50%);padding:12px;background:rgba(255,255,255,.75);border:1px solid ${neutral200};border-radius:8px;box-shadow:0 4px 12px rgba(17,24,39,.08);pointer-events:none;white-space:nowrap;transition:opacity .1s`;
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
    title.style.cssText = `color:${neutral800};font-weight:700;font-size:12px;margin-bottom:8px`;
    element.appendChild(title);

    for (const [label, value, color] of [
      ["시가", candle.openPrice, neutral950],
      ["고가", candle.highPrice, marketUp],
      ["저가", candle.lowPrice, marketDown],
      ["종가", candle.closePrice, neutral950],
      ["거래량", candle.volume, neutral300],
    ] as const) {
      const row = document.createElement("div");
      row.style.cssText = "display:flex;justify-content:space-between;gap:20px;font-size:12px";
      row.style.color = color;
      row.innerHTML = `<span>${label}</span><span>${label === "거래량" ? formatVolume(value) : formatPrice(value)}</span>`;
      element.appendChild(row);
    }

    const container = chart.canvas.parentElement;
    if (!container) return;

    element.style.opacity = "1";
    const left = Math.min(
      Math.max(tooltip.caretX, -12),
      container.clientWidth - element.offsetWidth - 12,
    );
    const top = Math.min(
      Math.max(tooltip.caretY, element.offsetHeight / 2),
      container.clientHeight - element.offsetHeight / 2,
    );
    element.style.left = `${left}px`;
    element.style.top = `${top}px`;
  };
  const data = {
    labels: candles.map((candle) => candle.timestamp),
    datasets: [
      {
        label: "종가",
        data: candles.map((candle) => candle.closePrice),
        borderColor: primaryColor,
        borderWidth: 2,
        pointRadius: (context: { dataIndex: number }) =>
          context.dataIndex === maxIndex || context.dataIndex === minIndex ? 3 : 0,
        pointBackgroundColor: primaryColor,
        pointBorderColor: primaryColor,
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
          layout: { padding: { top: 32, bottom: 32 } },
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
