"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Heart, RefreshCw } from "lucide-react";
import Card from "@/shared/ui/Card";
import StockLogo from "@/shared/ui/StockLogo";
import { getAccessToken } from "@/shared/api/base";
import { getWatchlist, toggleWatchlist } from "@/shared/api/watchlists";
import type { RankingType, StockRankingItem } from "@/entities/stock/types";

interface StockRankingSectionProps {
  rankings: Record<RankingType, StockRankingItem[]>;
  timestamp: string;
  onRefresh: () => void;
  refreshing: boolean;
}

const TABS: RankingType[] = ["상승률", "하락률", "거래대금", "거래량"];

export default function StockRankingSection({
  rankings,
  timestamp,
  onRefresh,
  refreshing,
}: StockRankingSectionProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<RankingType>("상승률");
  const [favorites, setFavorites] = useState<Record<string, boolean>>({});
  // 종목코드별로 "지금까지 보낸 요청들의 체인"과 "가장 최근에 보낸 요청 번호"를 들고 있는다.
  // 아래 toggleFavorite 주석 참고.
  const requestChain = useRef<Record<string, Promise<unknown>>>({});
  const latestRequestId = useRef<Record<string, number>>({});

  // 로그인 상태에서만 실제 관심종목 목록을 불러온다 — 비로그인이면 빈 상태로 둔다
  // (LikeButton과 동일 패턴: 하트 누를 때 로그인 안 돼있으면 그때 /login으로 보냄).
  useEffect(() => {
    if (!getAccessToken()) return;
    getWatchlist()
      .then((list) => setFavorites(Object.fromEntries(list.map((s) => [s.code, true]))))
      .catch(() => {
        // ponytail: 조회 실패는 조용히 무시 — 하트는 그냥 빈 상태로 보이고 눌러서 다시 시도 가능
      });
  }, []);

  // 낙관적 업데이트: 하트는 클릭 즉시 뒤집고, 실제 등록/해제는 백그라운드에서 서버와 맞춘다.
  // 서버 응답을 기다렸다가 화면을 바꾸면 그 네트워크 왕복 시간만큼 버튼이 굼떠 보인다 —
  // 실패했을 때만 원래 상태로 되돌리면 되고, 흔치 않은 실패를 위해 매번 기다릴 이유는 없다.
  // Redux/Redis는 이 목적(버튼 하나의 낙관적 토글)엔 과함 — 컴포넌트 로컬 상태로 충분.
  //
  // 1초 안에 여러 번 클릭할 때 겪었던 두 가지 버그와 수정 이유:
  // 1) "이미 요청 중이면 새 요청은 안 보냄" 방식이었을 때 — 맨 처음 요청의 응답이 나중에
  //    도착하면서 그 사이 여러 번 더 클릭해 만든 최신 화면을 덮어써서 엉뚱하게 보였다.
  // 2) 클릭마다 매번 서버로 보내되 응답만 "최신 것만 반영"하도록 고쳤더니, 이번엔 같은
  //    종목에 대한 토글 요청 여러 개가 서버에 동시에 도착해 DB에서 경합(같은 행을 동시에
  //    읽고 쓰다가 UNIQUE 제약 위반)해서 요청 하나가 통째로 실패하는 문제가 실제로 있었다
  //    (네트워크 로그로 확인: 요청 3개 중 응답 2개만 옴).
  // 그래서 지금은 같은 종목의 요청을 "체인"으로 순서대로 이어 보낸다 — 화면은 클릭마다
  // 바로 바뀌지만, 실제 서버 호출은 이전 것이 끝난 뒤에만 나가서 DB 경합 자체가 생기지
  // 않는다. 응답 반영은 여전히 "가장 최근 클릭"만 인정한다.
  const toggleFavorite = (code: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }

    const previous = !!favorites[code];
    setFavorites((prev) => ({ ...prev, [code]: !previous }));

    const requestId = (latestRequestId.current[code] ?? 0) + 1;
    latestRequestId.current[code] = requestId;

    const previousInChain = requestChain.current[code] ?? Promise.resolve();
    requestChain.current[code] = previousInChain.then(
      () => toggleWatchlist(code),
      () => toggleWatchlist(code), // 앞선 요청이 실패했어도 이 요청은 이어서 보낸다
    ).then(
      (result) => {
        if (latestRequestId.current[code] !== requestId) return; // 그 사이 더 최신 클릭이 있었음
        setFavorites((prev) => ({ ...prev, [code]: result.inWatchlist }));
      },
      () => {
        if (latestRequestId.current[code] !== requestId) return;
        setFavorites((prev) => ({ ...prev, [code]: previous }));
      },
    );
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
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* 가로 스크롤 탭 버튼 */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
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

              {/* 우측: 현재가 + 등락률 + 관심종목 하트 */}
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
                  aria-label={isFav ? "관심종목 해제" : "관심종목 등록"}
                  className="p-1 transition-transform active:scale-90"
                >
                  <Heart
                    size={20}
                    strokeWidth={1.8}
                    fill={isFav ? "currentColor" : "none"}
                    className={isFav ? "text-red-500" : "text-gray-400 dark:text-gray-500"}
                  />
                </button>
              </div>
            </Link>
          );
        })}
      </div>
    </Card>
  );
}
