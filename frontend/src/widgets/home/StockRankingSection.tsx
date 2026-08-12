"use client";

import { useState } from "react";
import Link from "next/link";
import Card from "@/shared/ui/Card";
import type { StockRankingMock } from "@/shared/mock/homeMockData";

interface StockRankingSectionProps {
  rankings: Record<string, StockRankingMock[]>;
  timestamp: string;
}

const TABS = ["인기검색", "상승률", "하락률", "거래대금", "거래량"];

export default function StockRankingSection({
  rankings,
  timestamp,
}: StockRankingSectionProps) {
  const [activeTab, setActiveTab] = useState("인기검색");
  const [favorites, setFavorites] = useState<Record<string, boolean>>({});

  const toggleFavorite = (code: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setFavorites((prev) => ({ ...prev, [code]: !prev[code] }));
  };

  const currentList = rankings[activeTab] || rankings["인기검색"] || [];

  return (
    <Card className="flex flex-col gap-4">
      {/* 타이틀 및 기준시각 */}
      <div className="flex items-center justify-between">
        <h3 className="text-[18px] font-bold text-heading">국내주식 랭킹</h3>
        <span className="text-[11px] font-medium text-caption">{timestamp}</span>
      </div>

      {/* 가로 스크롤 탭 버튼 */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        {TABS.map((tab) => {
          const isActive = tab === activeTab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`shrink-0 rounded-full px-3.5 py-1.5 text-[13px] font-semibold transition-all ${
                isActive
                  ? "bg-heading text-white shadow-sm dark:bg-white dark:text-heading"
                  : "bg-gray-100 text-caption hover:text-heading dark:bg-gray-800"
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* 종목 랭킹 리스트 */}
      <div className="flex flex-col divide-y divide-border-soft/60">
        {currentList.map((stock) => {
          const isFav = favorites[stock.code];
          return (
            <Link
              key={stock.code}
              href={`/stock/${stock.code}`}
              className="flex items-center justify-between py-3.5 transition-colors hover:bg-gray-50/50 dark:hover:bg-gray-800/20"
            >
              {/* 좌측: 로고 + 종목명 */}
              <div className="flex items-center gap-3">
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-full text-[11px] font-bold text-white shadow-sm ${stock.logoBg}`}
                >
                  {stock.logoText}
                </div>
                <span className="text-[16px] font-bold text-heading">
                  {stock.name}
                </span>
              </div>

              {/* 우측: 현재가 + 등락률 + 즐겨찾기 별 */}
              <div className="flex items-center gap-3 text-right">
                <div>
                  <p className="text-[15px] font-bold text-heading">
                    {stock.price}
                  </p>
                  <p
                    className={`text-[12px] font-bold ${
                      stock.isUp ? "text-market-up" : "text-market-down"
                    }`}
                  >
                    {stock.changePercent}
                  </p>
                </div>

                <button
                  onClick={(e) => toggleFavorite(stock.code, e)}
                  className="p-1 text-gray-400 hover:text-yellow-400 dark:text-gray-500"
                >
                  {isFav ? (
                    <span className="text-[18px] text-yellow-400">★</span>
                  ) : (
                    <span className="text-[18px]">☆</span>
                  )}
                </button>
              </div>
            </Link>
          );
        })}
      </div>
    </Card>
  );
}
