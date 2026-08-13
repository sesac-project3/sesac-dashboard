import PageContainer from "@/shared/ui/PageContainer";
import MarketIndexCarousel from "@/widgets/home/MarketIndexCarousel";
import AiMarketIssueCard from "@/widgets/home/AiMarketIssueCard";
import StockRankingSection from "@/widgets/home/StockRankingSection";
import { MOCK_INDICES, MOCK_AI_ISSUE, MOCK_RANKINGS } from "@/shared/mock/homeMockData";

// 로그인 상태(HomeGate)에서 보여주는 홈 대시보드. PR #34(feat/home-layout)의 새 레이아웃을
// 그대로 쓴다 — 지수 캐러셀 / AI 이슈 요약 / 랭킹 섹션 (아직 mock, 실 데이터 연동은 별도 작업).
export default function MarketDashboard() {
  return (
    <PageContainer>
      <div className="flex flex-col gap-4 py-4 pb-12">
        {/* 1. 코스피 / 코스닥 지수 캐러셀 & 수급 카드 */}
        <MarketIndexCarousel indices={MOCK_INDICES} />

        {/* 2. 국내 주요 이슈 AI 요약 카드 */}
        <AiMarketIssueCard
          title={MOCK_AI_ISSUE.title}
          text={MOCK_AI_ISSUE.text}
          timestamp={MOCK_AI_ISSUE.timestamp}
        />

        {/* 3. 국내주식 랭킹 섹션 (인기검색, 상승률, 하락률, 거래대금, 거래량 탭) */}
        <StockRankingSection rankings={MOCK_RANKINGS} timestamp="2026/08/12 14:55 기준" />
      </div>
    </PageContainer>
  );
}
