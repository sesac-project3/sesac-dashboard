"use client";

import type { ExchangeRateMock } from "@/shared/mock/homeMockData";

interface ExchangeRateBarProps {
  rates: ExchangeRateMock[];
}

export default function ExchangeRateBar({ rates }: ExchangeRateBarProps) {
  if (!rates || rates.length === 0) return null;

  return (
    <div className="flex items-center gap-4 overflow-x-auto rounded-xl bg-gray-50/80 px-4 py-2.5 text-[13px] whitespace-nowrap scrollbar-none dark:bg-gray-800/40">
      {rates.map((r) => (
        <div key={r.currency} className="flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${
              r.isUp ? "bg-red-500" : "bg-blue-500"
            }`}
          />
          <span className="font-medium text-caption">{r.currency}</span>
          <span className="font-bold text-heading">{r.value}</span>
          <span
            className={`font-semibold ${
              r.isUp ? "text-market-up" : "text-market-down"
            }`}
          >
            {r.changePercent}
          </span>
        </div>
      ))}
    </div>
  );
}
