"use client";

import { useState } from "react";
import Card from "@/shared/ui/Card";
import type { MarketIndexMock } from "@/shared/mock/homeMockData";

interface MarketIndexCarouselProps {
  indices: MarketIndexMock[];
}

export default function MarketIndexCarousel({ indices }: MarketIndexCarouselProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (!indices || indices.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      {/* 캐러셀 스와이프 카드 영역 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
                  {idx.value}
                </span>
              </div>
              <p
                className={`mt-0.5 text-[14px] font-bold ${
                  idx.isUp ? "text-market-up" : "text-market-down"
                }`}
              >
                ▲ {idx.change} ({idx.changePercent})
              </p>
            </div>

            {/* 주체별 수급 현황 (개인, 외국인, 기관) */}
            <div className="mt-1 flex items-center justify-between border-t border-border-soft/60 pt-2.5 text-[12px]">
              <div className="flex flex-col items-center">
                <span className="text-caption">개인</span>
                <span
                  className={`mt-0.5 font-bold ${
                    idx.investors.personal >= 0 ? "text-market-up" : "text-market-down"
                  }`}
                >
                  {idx.investors.personal.toLocaleString()}
                </span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-caption">외국인</span>
                <span
                  className={`mt-0.5 font-bold ${
                    idx.investors.foreign >= 0 ? "text-market-up" : "text-market-down"
                  }`}
                >
                  {idx.investors.foreign.toLocaleString()}
                </span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-caption">기관</span>
                <span
                  className={`mt-0.5 font-bold ${
                    idx.investors.inst >= 0 ? "text-market-up" : "text-market-down"
                  }`}
                >
                  {idx.investors.inst.toLocaleString()}
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* 하단 인디케이터 도트 및 전체보기 */}
      <div className="flex items-center justify-between px-1 text-[12px] text-caption">
        <span>투자자동향 : 금액(억원)</span>
        <div className="flex items-center gap-1.5">
          {indices.map((_, i) => (
            <button
              key={i}
              onClick={() => setActiveIndex(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === activeIndex ? "w-4 bg-heading" : "w-1.5 bg-gray-300 dark:bg-gray-700"
              }`}
            />
          ))}
        </div>
        <button className="font-medium text-caption hover:text-heading">
          전체보기 &gt;
        </button>
      </div>
    </div>
  );
}
