"use client";

import { Heart, Triangle } from "lucide-react";

import type { Quote } from "@/entities/stock/chart-types";

export default function StockQuoteCard({
  stockCode,
  stockName,
  market,
  exchange,
  quote,
}: {
  stockCode: string;
  stockName: string;
  market: string;
  exchange: string;
  quote: Quote | null;
}) {
  const isDown = quote?.changeDirection === "DOWN";
  const color = !quote ? "text-caption" : isDown ? "text-market-down" : "text-market-up";

  return (
    <div className="flex flex-col gap-[14px] px-5 pt-6 pb-4">
      <div className="relative flex flex-col gap-1">
        <button
          type="button"
          aria-label="관심종목 추가"
          className="absolute top-0 right-0 cursor-pointer text-heading"
        >
          <Heart aria-hidden="true" size={24} strokeWidth={1.8} />
        </button>
        <h1 className="text-[28px] leading-none font-bold tracking-[-0.04em] text-heading">
          {stockName}
        </h1>
        <p className="text-[14px] leading-none text-caption">
          {stockCode} <span aria-hidden="true">|</span> {market} <span aria-hidden="true">|</span>{" "}
          {exchange}
        </p>
      </div>
      {quote ? (
        <div className="flex flex-col gap-2">
          <p className={`text-[40px] leading-none font-bold tracking-[-0.04em] ${color}`}>
            {quote.currentPrice.toLocaleString()}
          </p>
          <div className={`flex min-h-6 items-center gap-3 text-[18px] leading-none font-medium ${color}`}>
              <span className="flex items-center gap-1">
                <Triangle
                  aria-hidden="true"
                  className={isDown ? "rotate-180" : ""}
                  fill="currentColor"
                  height={16}
                  width={16}
                  strokeWidth={0}
                />
                {Math.abs(quote.changePrice).toLocaleString()}
              </span>
              <span className="h-4 w-px bg-border" aria-hidden="true" />
              <span>{quote.changeRate >= 0 ? "+" : "-"}{Math.abs(quote.changeRate).toFixed(2)}%</span>
          </div>
        </div>
      ) : (
        <div className="flex animate-pulse flex-col gap-2" aria-label="시세를 불러오는 중" aria-busy="true">
          <span className="h-10 w-56 rounded-md bg-surface" />
          <span className="h-6 w-40 rounded-md bg-surface" />
        </div>
      )}
    </div>
  );
}
