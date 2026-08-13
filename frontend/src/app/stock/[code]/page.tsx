import StockLiveSection from "@/features/stock-quote/StockLiveSection";
import { Sparkles } from "lucide-react";
import { API_BASE_URL } from "@/shared/config/env";
import type { StockReport } from "@/entities/report/types";
import type { Stock } from "@/entities/stock/types";
import PageContainer from "@/shared/ui/PageContainer";
import Card from "@/shared/ui/Card";
import PillButton from "@/shared/ui/PillButton";

async function fetchReport(code: string): Promise<StockReport | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/reports/${code}`, { cache: "no-store" });
    if (!res.ok) return null;
    const body = await res.json(); // ApiResponse 봉투
    return body.data;
  } catch {
    return null;
  }
}

async function fetchStock(code: string): Promise<Stock | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/stocks`, { cache: "no-store" });
    if (!res.ok) return null;
    const body = await res.json();
    return (body.data as Stock[]).find((stock) => stock.code === code) ?? null;
  } catch {
    return null;
  }
}

// DESIGN_SPEC.md §11.3: 매수 red / 매도 blue (국내 증시 convention 연장), 중립은 gray.
const JUDGEMENT_COLOR: Record<string, string> = {
  매수: "text-market-up",
  매도: "text-market-down",
  중립: "text-caption",
};

// DESIGN_SPEC.md §15.2 Summary Card — 리포트 생성 전 항상 보여주는 준비 중 상태(3항목 고정 카피).
const PREPARING_ITEMS = [
  {
    title: "AI 종합 의견 준비 중",
    description: "종목 분석이 끝나면 핵심 투자 관점을 이곳에 요약해 보여줍니다.",
    badge: "bg-primary-soft/15 text-primary-soft",
  },
  {
    title: "성장 포인트 확인 중",
    description: "수급, 실적, 가격 흐름을 바탕으로 성장 요인을 정리하고 있습니다.",
    badge: "bg-positive/15 text-positive",
  },
  {
    title: "리스크 체크 준비 중",
    description: "변동성과 최신 뉴스 흐름을 분석해 주의 포인트를 곧 반영합니다.",
    badge: "bg-danger/15 text-danger",
  },
] as const;

export default async function StockReportPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const [report, stock] = await Promise.all([fetchReport(code), fetchStock(code)]);
  const hasJudgement = report?.judgement && report.judgementReasons?.length;

  return (
    <PageContainer>
      <div className="flex flex-col gap-4 pb-8">
        <StockLiveSection
          stockCode={code}
          stockName={stock?.name ?? code}
          market={stock?.market === "KOSDAQ" ? "코스닥" : "코스피"}
        />

      <div className="flex flex-col gap-4 px-5">
        <PillButton className="self-center !w-[80%] px-6">AI 리포트 보기</PillButton>
        <p className="text-center text-[12px] leading-[1.5] text-caption">
          본 정보는 투자 참고 자료이며 투자 권유가 아닙니다.
          <br />
          투자 판단과 그 결과에 대한 책임은 이용자 본인에게 있습니다.
        </p>
        </div>
      </div>
    </PageContainer>
  );
}
