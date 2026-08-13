"use client";

import { useState } from "react";
import Link from "next/link";
import Card from "@/shared/ui/Card";
import type { RankingType, StockRankingItem } from "@/entities/stock/types";

interface StockRankingSectionProps {
  rankings: Record<RankingType, StockRankingItem[]>;
  timestamp: string;
  onRefresh: () => void;
  refreshing: boolean;
}

const TABS: RankingType[] = ["상승률", "하락률", "거래대금", "거래량"];

// 종목코드 기준 fallback(색/이니셜) — public/icons/stocks/{코드}.png가 없거나 로드 실패할 때만 씀.
const LOGO_FALLBACK: Record<string, { bg: string; text: string }> = {
  "005930": { bg: "bg-blue-600", text: "SEC" },
  "000660": { bg: "bg-red-500", text: "SK" },
  "005380": { bg: "bg-blue-700", text: "HD" },
  "373220": { bg: "bg-emerald-600", text: "LGE" },
  "042660": { bg: "bg-orange-500", text: "한화" },
};

function StockLogo({ code, name }: { code: string; name: string }) {
  const [failed, setFailed] = useState(false);

  if (!failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- public/ 정적 아이콘 5개뿐, next/image 불필요
      <img
        src={`/icons/stocks/${code}.png`}
        alt={name}
        className="h-9 w-9 shrink-0 rounded-full object-cover shadow-sm"
        onError={() => setFailed(true)}
      />
    );
  }

  const fallback = LOGO_FALLBACK[code] ?? { bg: "bg-gray-400", text: name.slice(0, 2) };
  return (
    <div
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white shadow-sm ${fallback.bg}`}
    >
      {fallback.text}
    </div>
  );
}

export default function StockRankingSection({
  rankings,
  timestamp,
  onRefresh,
  refreshing,
}: StockRankingSectionProps) {
  const [activeTab, setActiveTab] = useState<RankingType>("상승률");
  const [favorites, setFavorites] = useState<Record<string, boolean>>({});

  const toggleFavorite = (code: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setFavorites((prev) => ({ ...prev, [code]: !prev[code] }));
  };

  const currentList = rankings[activeTab] ?? [];

  return (
    <Card className="flex flex-col gap-4">
      {/* 타이틀 및 기준시각 + 새로고침 */}
      <div className="flex items-center justify-between">
        <h3 className="text-[18px] font-bold text-heading">국내주식 랭킹</h3>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium text-caption">{timestamp}</span>
          <button
            onClick={onRefresh}
            disabled={refreshing}
            aria-label="새로고침"
            className="p-0.5 text-caption transition-transform hover:text-heading disabled:opacity-50"
          >
            <svg
              viewBox="0 0 24 24"
              className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 12a9 9 0 0 1 15.3-6.4L21 8" />
              <path d="M21 3v5h-5" />
              <path d="M21 12a9 9 0 0 1-15.3 6.4L3 16" />
              <path d="M3 21v-5h5" />
            </svg>
          </button>
        </div>
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
                <StockLogo code={stock.code} name={stock.name} />
                <span className="text-[16px] font-bold text-heading">{stock.name}</span>
              </div>

              {/* 우측: 현재가 + 등락률 + 즐겨찾기 별 */}
              <div className="flex items-center gap-3 text-right">
                <div>
                  <p className="text-[15px] font-bold text-heading">
                    {stock.price.toLocaleString()}원
                  </p>
                  <p
                    className={`text-[12px] font-bold ${
                      stock.isUp ? "text-market-up" : "text-market-down"
                    }`}
                  >
                    {stock.isUp ? "+" : "-"}
                    {Math.abs(stock.change).toLocaleString()} ({stock.isUp ? "+" : ""}
                    {stock.changePercent.toFixed(2)}%)
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
