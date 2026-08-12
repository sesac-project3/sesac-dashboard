import { API_BASE_URL } from "@/shared/config/env";
import type { StockReport } from "@/entities/report/types";
import PageContainer from "@/shared/ui/PageContainer";
import Card from "@/shared/ui/Card";

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
  const report = await fetchReport(code);
  const hasJudgement = report?.judgement && report.judgementReasons?.length;

  return (
    <PageContainer>
      {/* DESIGN_SPEC.md §13.2 Stock Header 간소화판 — 종목명/시장 정보가 아직 없어(백엔드
          미연동) 종목코드만 title로 노출. 없는 데이터를 임의로 만들지 않는다(§22). */}
      <h1 className="py-6 text-center text-[22px] font-semibold text-heading">{code}</h1>

      <div className="flex flex-col gap-4 pb-8">
        {/* §13.3 Price Hero — currentPrice가 없으면(리포트 미생성) 통째로 숨긴다 */}
        {report?.currentPrice != null && (
          <Card>
            <p className="text-[38px] leading-[1.1] font-bold tracking-[-0.03em] text-heading">
              {report.currentPrice.toLocaleString()}원
            </p>
          </Card>
        )}

        {/* §21 AI Report Section — 근거 있을 때만 노출(F-03-1 규칙) */}
        {hasJudgement ? (
          <Card>
            <h2 className="mb-3 text-[18px] font-semibold text-heading">투자 판단 요약</h2>
            <p className={`text-[20px] font-bold ${JUDGEMENT_COLOR[report!.judgement!] ?? ""}`}>
              {report!.judgement}
            </p>
            <ul className="mt-3 flex flex-col gap-2">
              {report!.judgementReasons!.map((reason, i) => (
                <li key={i} className="flex items-start gap-2 text-[14px] leading-[1.6] text-heading">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </Card>
        ) : (
          // §15.2 — 리포트가 아직 없을 때의 고정 안내 카드 (빈 값 조작 금지)
          <Card className="flex flex-col gap-6">
            <h2 className="flex items-center gap-2 text-[18px] font-semibold text-heading">
              <span className="text-primary-soft">✦</span> AI 분석 리포트 요약
            </h2>
            {PREPARING_ITEMS.map((item, i) => (
              <div key={item.title} className="flex items-start gap-3">
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[13px] font-semibold ${item.badge}`}
                >
                  {i + 1}
                </span>
                <div>
                  <p className="text-[16px] font-semibold text-heading">{item.title}</p>
                  <p className="mt-1 text-[14px] leading-[1.5] text-caption">{item.description}</p>
                </div>
              </div>
            ))}
          </Card>
        )}

        <p className="text-center text-[12px] leading-[1.5] text-caption">
          본 정보는 투자 참고 자료이며 투자 권유가 아닙니다.
          <br />
          투자 판단과 그 결과에 대한 책임은 이용자 본인에게 있습니다.
        </p>
      </div>
    </PageContainer>
  );
}
