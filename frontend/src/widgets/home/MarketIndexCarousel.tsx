"use client";

import { useState } from "react";
import { Triangle } from "lucide-react";
import Card from "@/shared/ui/Card";
import type { MarketIndexDetail } from "@/entities/stock/types";

interface MarketIndexCarouselProps {
  indices: MarketIndexDetail[];
}

export default function MarketIndexCarousel({ indices }: MarketIndexCarouselProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (!indices || indices.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      {/* 캐러셀 스와이프 카드 영역 */}
      {/* sm(640px) 대신 400px부터 2열로 — 모바일 폭에서도 코스피/코스닥이 나란히 보이도록 */}
      <div className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2">
        {indices.map((idx, i) => (
          <Card
            key={idx.title}
            className={`flex flex-col gap-3 border transition-all ${
              i === activeIndex
                ? "border-primary/40 shadow-md dark:border-primary/50"
                : "border-border-soft opacity-90"
            }`}
            onClick={() => setActiveIndex(i)}
          >
            {/* 타이틀 및 지수 수치 */}
            <div>
              <p className="text-[13px] font-medium text-caption">{idx.title}</p>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-[28px] font-bold tracking-tight text-heading">
                  {idx.value.toLocaleString()}
                </span>
              </div>
              <p
                className={`mt-0.5 text-[14px] font-bold ${
                  idx.isUp ? "text-market-up" : "text-market-down"
                }`}
              >
                <Triangle className={`mr-1 inline h-3 w-3 ${idx.isUp ? "" : "rotate-180"}`} fill="currentColor" strokeWidth={0} aria-hidden="true" />
                {Math.abs(idx.change).toLocaleString()} (
                {idx.isUp ? "+" : ""}
                {idx.changePercent.toFixed(2)}%)
              </p>
            </div>

            {/* 주체별 수급 현황 (개인, 외국인, 기관) */}
            <div className="mt-1 flex items-center justify-between border-t border-border-soft/60 pt-2.5 text-[12px]">
              {(
                [
                  { label: "개인", value: idx.investors.personal },
                  { label: "외국인", value: idx.investors.foreign },
                  { label: "기관", value: idx.investors.institution },
                ] as const
              ).map((row) => (
                <div key={row.label} className="flex flex-col items-center">
                  <span className="text-caption">{row.label}</span>
                  <span
                    className={`mt-0.5 font-bold ${
                      row.value >= 0 ? "text-market-up" : "text-market-down"
                    }`}
                  >
                    {row.value.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
