"use client";

import { useCallback, useEffect, useState } from "react";
import PageContainer from "@/shared/ui/PageContainer";
// import HomeLoadingScreen from "@/widgets/home/HomeLoadingScreen"; // ponytail: 로딩화면 로직과 같이 임시 비활성화
import MarketIndexCarousel from "@/widgets/home/MarketIndexCarousel";
import AiMarketIssueCard from "@/widgets/home/AiMarketIssueCard";
import StockRankingSection from "@/widgets/home/StockRankingSection";
import { getHomeDashboard } from "@/shared/api/stocks";
import type { HomeDashboard } from "@/entities/stock/types";
import { MOCK_AI_ISSUE } from "@/shared/mock/homeMockData";

function formatAsOf(iso: string) {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())} 기준`;
}

// 로그인 상태(HomeGate)에서 보여주는 홈 대시보드. 지수/투자자동향/랭킹은 KIS Open API 실데이터
// (/stocks/home-dashboard)를 클라이언트에서 fetch — 랭킹 카드의 새로고침 버튼이 다시 부르는
// 것도 이 함수다. AI 이슈 카드는 이번 작업 범위 밖이라 기존 mock 유지.
export default function MarketDashboard() {
  const [data, setData] = useState<HomeDashboard | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);
  // ponytail: 로딩화면 로직 임시 주석처리 (요청으로 비활성화, 필요해지면 복구)
  // // 최초 로딩 화면: 데이터/에러가 도착하면 진행률 100%를 0.3초 보여준 뒤 실제 화면으로 전환.
  // // doneRef로 "최초 1회"만 걸리게 해서, 5초 주기 자동 갱신 때는 이 화면이 다시 뜨지 않는다.
  // const [showLoadingScreen, setShowLoadingScreen] = useState(true);
  // const initialLoadHandledRef = useRef(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const result = await getHomeDashboard();
      if (result) {
        setData(result);
        setError(false);
      } else {
        setError(true);
      }
    } catch {
      setError(true);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    // 5초마다 자동 갱신 — KIS 호출 한도(초당 20건, 앱키는 전체 사용자 공유)를 감안해
    // 그보다 훨씬 낮은 주기로만 돈다. 새로고침 버튼은 이 interval과 별개로 즉시 재호출.
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  // useEffect(() => {
  //   if ((data || error) && !initialLoadHandledRef.current) {
  //     initialLoadHandledRef.current = true;
  //     const timer = setTimeout(() => setShowLoadingScreen(false), 300);
  //     return () => clearTimeout(timer);
  //   }
  // }, [data, error]);

  // if (showLoadingScreen) {
  //   return <HomeLoadingScreen percent={data || error ? 100 : 0} />;
  // }
  if (!data && !error) {
    return null;
  }

  if (!data) {
    // DESIGN_SPEC.md §23.3 Error state
    return (
      <PageContainer>
        <div className="mt-4 flex flex-col items-center gap-4 rounded-lg border border-border-soft bg-white py-12 text-center shadow-card">
          <p className="text-[14px] text-caption">
            시세 데이터를 불러오지 못했어요.
            <br />
            잠시 후 다시 시도해주세요.
          </p>
          <button
            onClick={load}
            className="rounded-sm bg-primary px-5 py-2.5 text-[14px] font-medium text-white active:scale-[0.98]"
          >
            다시 시도
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="flex flex-col gap-4 py-4 pb-12">
        {/* 1. 코스피 / 코스닥 지수 캐러셀 & 수급 카드 */}
        <MarketIndexCarousel indices={data.indices} />

        {/* 2. 국내 주요 이슈 AI 요약 카드 */}
        <AiMarketIssueCard
          title={MOCK_AI_ISSUE.title}
          text={MOCK_AI_ISSUE.text}
          timestamp={MOCK_AI_ISSUE.timestamp}
        />

        {/* 3. 국내주식 랭킹 섹션 (상승률/하락률/거래대금/거래량, 새로고침 가능) */}
        <StockRankingSection
          rankings={data.rankings}
          timestamp={formatAsOf(data.asOf)}
          onRefresh={load}
          refreshing={refreshing}
        />
      </div>
    </PageContainer>
  );
}
