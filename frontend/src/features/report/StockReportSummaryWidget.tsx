"use client";

import { useState } from "react";
import { Sparkles, ArrowRight } from "lucide-react";
import type { StockReport } from "@/entities/report/types";
import AiReportDetailModal from "./AiReportDetailModal";
import Card from "@/shared/ui/Card";
import PillButton from "@/shared/ui/PillButton";

interface StockReportSummaryWidgetProps {
  report: StockReport | null;
  stockName: string;
  stockCode: string;
}

const PREPARING_ITEMS = [
  {
    title: "1. AI 종합 의견 준비 중",
    description: "종목 분석이 끝나면 핵심 투자 관점을 이곳에 요약해 보여줍니다.",
  },
  {
    title: "2. 성장 포인트 확인 중",
    description: "수급, 실적, 가격 흐름을 바탕으로 성장 요인을 정리하고 있습니다.",
  },
  {
    title: "3. 리스크 체크 준비 중",
    description: "변동성과 최신 뉴스 흐름을 분석해 주의 포인트를 곧 반영합니다.",
  },
] as const;

export default function StockReportSummaryWidget({
  report,
  stockName,
  stockCode,
}: StockReportSummaryWidgetProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const judgementText =
    report?.judgement === "BUY" || report?.judgement === "매수"
      ? "매수 (Buy)"
      : report?.judgement === "SELL" || report?.judgement === "매도"
      ? "매도 (Sell)"
      : "보유 (Hold)";

  const judgementBadgeStyle =
    report?.judgement === "BUY" || report?.judgement === "매수"
      ? "text-[#F04452] bg-[#FEE9E8]"
      : report?.judgement === "SELL" || report?.judgement === "매도"
      ? "text-[#3182F6] bg-[#E8F3FF]"
      : "text-[#FF9500] bg-[#FFF5E6]";

  return (
    <>
      <Card className="flex flex-col gap-4 p-5 bg-white border border-slate-200/80 text-[#191F28] rounded-2xl shadow-sm">
        {/* 카드 헤더 */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-[#3182F6]" />
            <h3 className="font-bold text-[#191F28] text-base">AI 분석 리포트 요약</h3>
          </div>
          <span className="text-[11px] text-[#8B95A1]">Updated 방금 전</span>
        </div>

        {/* 카드 본문 */}
        {report ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className={`px-3 py-1 text-xs font-extrabold rounded-lg ${judgementBadgeStyle}`}>
                {judgementText}
              </span>
              <span className="text-xs font-bold text-[#333D4B]">
                {report.qualitativeSignal ?? "지표 분석 완료"}
              </span>
            </div>

            {report.investmentSummary && (
              <p className="text-xs leading-relaxed text-[#4E5968] bg-[#F2F4F6] p-3.5 rounded-xl font-normal">
                {report.investmentSummary}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {PREPARING_ITEMS.map((item, idx) => (
              <div key={idx} className="rounded-xl bg-[#F9FAFB] p-3.5 space-y-1 border border-slate-100">
                <h4 className="text-xs font-bold text-[#333D4B]">{item.title}</h4>
                <p className="text-[11px] text-[#6B7684]">{item.description}</p>
              </div>
            ))}
          </div>
        )}

        {/* 리포트 전체 보기 CTA 버튼 */}
        <PillButton
          onClick={() => setIsModalOpen(true)}
          className="w-full flex items-center justify-center gap-2 py-3 text-xs font-bold bg-[#3182F6] hover:bg-[#1B64DA] text-white rounded-xl shadow-sm transition"
        >
          <span>리포트 전체 보기</span>
          <ArrowRight className="h-4 w-4" />
        </PillButton>
      </Card>

      {/* AI 리포트 상세 모달 */}
      <AiReportDetailModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        report={report}
        stockName={stockName}
      />
    </>
  );
}
