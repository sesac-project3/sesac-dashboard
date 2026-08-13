import PageContainer from "@/shared/ui/PageContainer";
import MarketIndexCarousel from "@/widgets/home/MarketIndexCarousel";
import AiMarketIssueCard from "@/widgets/home/AiMarketIssueCard";
import StockRankingSection from "@/widgets/home/StockRankingSection";
import {
  MOCK_INDICES,
  MOCK_AI_ISSUE,
  MOCK_RANKINGS,
} from "@/shared/mock/homeMockData";

export default function HomePage() {
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
        <StockRankingSection
          rankings={MOCK_RANKINGS}
          timestamp="2026/08/12 14:55 기준"
        />
      </div>
    </PageContainer>
  );
}
