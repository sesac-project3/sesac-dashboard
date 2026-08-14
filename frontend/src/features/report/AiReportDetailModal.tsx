"use client";

import { useState } from "react";
import { X, Sparkles, TrendingUp, AlertTriangle, Newspaper, Scale, BarChart2, Lightbulb } from "lucide-react";
import type { StockReport, PeerComparisonRow } from "@/entities/report/types";
import { withTopicParticle } from "@/shared/lib/korean";
import Button from "@/shared/ui/Button";

interface AiReportDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: StockReport | null;
  stockName: string;
  // 실시간 시세 — 없으면(웹소켓 연결 전 등) report.currentPrice로 fallback.
  livePrice?: number;
}

export default function AiReportDetailModal({
  isOpen,
  onClose,
  report,
  stockName,
  livePrice,
}: AiReportDetailModalProps) {
  // 동종업계 비교 탭 상태 ("opm" | "per" | "pbr" | "roe")
  const [peerTab, setPeerTab] = useState<"opm" | "per" | "pbr" | "roe">("opm");

  // 부모(StockReportSummaryWidget)가 이 모달을 항상 마운트해두고 isOpen prop만 토글하는
  // 구조라, 언마운트 지연 없이 isOpen을 그대로 CSS 트랜지션에 물리면 열고 닫을 때 둘 다
  // 자연스럽게 애니메이션된다 — DOM에서 안 사라지니 exit 트랜지션이 항상 재생된다.
  if (!report) return null;

  const getPeerValue = (peer: PeerComparisonRow, tab: "opm" | "per" | "pbr" | "roe") => {
    if (tab === "opm") return peer.operating_margin ?? peer.operatingMargin ?? null;
    if (tab === "per") return peer.per ?? null;
    if (tab === "pbr") return peer.pbr ?? null;
    if (tab === "roe") return peer.roe ?? null;
    return null;
  };

  const formatPeerValue = (val: number | null | undefined, tab: "opm" | "per" | "pbr" | "roe") => {
    if (val === null || val === undefined || isNaN(val)) return "데이터 없음";
    if (tab === "opm" || tab === "roe") return `${val.toFixed(1)}%`;
    return `${val.toFixed(1)}배`;
  };



  const judgementText =
    report.judgement === "BUY" || report.judgement === "매수"
      ? "매수 (Buy)"
      : report.judgement === "SELL" || report.judgement === "매도"
        ? "매도 (Sell)"
        : "보유 (Hold)";

  const judgementColor =
    report.judgement === "BUY" || report.judgement === "매수"
      ? "text-danger bg-surface-danger"
      : report.judgement === "SELL" || report.judgement === "매도"
        ? "text-info bg-surface-info"
        : "text-warning bg-surface-warning";

  // 52주 위치 계산 %
  const week52High = report.week52High ?? 1;
  const week52Low = report.week52Low ?? 0;
  const currentPrice = livePrice ?? report.currentPrice ?? 0;
  const priceBandRatio =
    week52High > week52Low
      ? Math.min(100, Math.max(0, ((currentPrice - week52Low) / (week52High - week52Low)) * 100))
      : 50;

  // 리스크 레벨 구하기 (시안 맞춤)
  const getRiskInfo = (score: number | undefined) => {
    if (score === undefined || score >= 75) {
      return { label: "높음 (High)", textColor: "text-danger", barColor: "bg-danger", widthPercent: 78 };
    }
    if (score >= 45) {
      return { label: "보통 (Medium)", textColor: "text-warning", barColor: "bg-warning", widthPercent: 50 };
    }
    return { label: "낮음 (Low)", textColor: "text-warning", barColor: "bg-warning", widthPercent: 32 };
  };


  return (
    <div
      className={`fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm transition-opacity duration-300 ease-out ${
        isOpen ? "opacity-100" : "pointer-events-none opacity-0"
      }`}
      aria-hidden={!isOpen}
      onClick={onClose}
    >
      <div
        className={`relative flex h-[90vh] w-full max-w-[480px] flex-col overflow-hidden rounded-t-3xl border border-neutral-200 bg-neutral-50 text-neutral-950 shadow-2xl transition-transform duration-300 ease-out ${
          isOpen ? "translate-y-0" : "translate-y-full"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 모달 헤더 */}
        <div className="flex items-center justify-between border-b border-neutral-200/80 px-6 py-4 bg-white sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-info" />
            <h2 className="text-lg font-bold text-neutral-950">AI 리포트 상세</h2>
          </div>
          <Button
            variant="icon"
            onClick={onClose}
            className="rounded-full p-1.5 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* 모달 본문 스크롤 영역 */}
        <div className="no-scrollbar flex-1 overflow-y-auto p-6 space-y-6 bg-neutral-50">
          {/* 히어로 배너 (밝은 토스 블루 스타일) */}
          <div className="rounded-2xl bg-info p-6 text-white shadow-md">
            <span className="text-xs font-semibold text-white/80 uppercase tracking-wider">
              {stockName} ({report.stockCode})
            </span>
          <h3 className="mt-1 text-xl font-bold leading-snug">
              {withTopicParticle(stockName)} {report.qualitativeSignal ?? "실적 및 퀀트 지표 분석 구간"}
            </h3>
            <p className="mt-2 text-xs text-white/80">
              {report.reportDate} 기준 분석
            </p>
          </div>

          {/* 블록 1. 투자 판단 요약 */}
          <div className="rounded-2xl border border-neutral-200/80 bg-white p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 border-b border-neutral-100 pb-3">
              <TrendingUp className="h-5 w-5 text-info" />
              <h4 className="font-bold text-neutral-950 text-base">1. 투자 판단 요약</h4>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl bg-neutral-50 p-4 flex flex-col justify-center items-center text-center border border-neutral-100">
                <span className="text-xs text-neutral-500 font-medium mb-1.5">AI 종합 의견</span>
                <span className={`inline-block px-3.5 py-1 text-sm font-extrabold rounded-lg ${judgementColor}`}>
                  {judgementText}
                </span>
              </div>
              <div className="rounded-xl bg-neutral-50 p-4 flex flex-col justify-center items-center text-center border border-neutral-100">
                <span className="text-xs text-neutral-500 font-medium mb-1.5">정성적 지표 상태</span>
              <span className="text-xs font-bold text-neutral-800 leading-tight">
                  {report.qualitativeSignal ?? "분석 완료"}
                </span>
              </div>
            </div>

            {report.investmentSummary && (
              <p className="text-xs leading-relaxed text-neutral-700 bg-neutral-100 p-4 rounded-xl font-normal">
                {report.investmentSummary}
              </p>
            )}

            {report.judgementReasons && report.judgementReasons.length > 0 && (
              <ul className="space-y-1.5 pt-1">
                {report.judgementReasons.map((reason, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-neutral-500">
                    <span className="text-info font-bold">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* 블록 2. 성장성 분석 */}
          <div className="rounded-2xl border border-neutral-200/80 bg-white p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
              <div className="flex items-center gap-2">
              <BarChart2 className="h-5 w-5 text-info" />
              <h4 className="font-bold text-neutral-950 text-base">2. 성장성 분석</h4>
              </div>
              <span className="text-xs text-neutral-500">(단위: 조원)</span>
            </div>

            {report.financials && report.financials.length > 0 ? (
              <div className="grid grid-cols-5 gap-2 pt-2">
                {report.financials.map((fin, idx) => {
                  const revMax = Math.max(...report.financials!.map((f) => f.revenue));
                  const heightPercent = revMax > 0 ? Math.max(25, (fin.revenue / revMax) * 100) : 50;
                  const isLatest = idx === report.financials!.length - 1;
                  return (
                    <div key={fin.fiscalYear} className="flex flex-col items-center gap-2">
                      <span className={`text-[10px] font-bold ${isLatest ? "text-info" : "text-neutral-500"}`}>
                        {fin.revenue > 1000000000
                          ? (fin.revenue / 10000000000).toFixed(1)
                          : fin.revenue > 1000
                            ? (fin.revenue / 1000).toFixed(1)
                            : fin.revenue.toFixed(1)}
                      </span>
                      <div className="h-28 w-full bg-neutral-100 rounded-xl flex items-end p-1">
                        <div
                            className={`w-full rounded-lg transition-all duration-500 ${isLatest ? "bg-info" : "bg-neutral-300"
                            }`}
                          style={{ height: `${heightPercent}%` }}
                        />
                      </div>
                      <span className="text-xs text-neutral-500">{fin.fiscalYear}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-neutral-500">재무 정보를 불러오는 중입니다.</p>
            )}

            <div className="rounded-xl bg-surface-info p-4 text-xs text-info font-normal leading-relaxed">
              <span className="font-bold text-info">AI View: </span>
              {stockName}의 매출 트렌드는 <span className="font-bold text-neutral-950">{report.revenueTrend ?? "성장"}</span> 추세를 나타내고 있으며, 영업이익률은 <span className="font-bold text-neutral-950">{report.operatingMarginTrend ?? "개선"}</span>되는 흐름입니다.
            </div>
          </div>

          {/* 블록 3. 리스크 체크 */}
          <div className="rounded-2xl border border-neutral-200/80 bg-white p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 border-b border-neutral-100 pb-3">
              <AlertTriangle className="h-5 w-5 text-warning" />
              <h4 className="font-bold text-neutral-950 text-base">3. 리스크 체크</h4>
            </div>

            <div className="space-y-4 text-xs">
              {/* 시장 변동성 */}
              {(() => {
                const info = getRiskInfo(report.riskScores?.["시장변동성"]);
                return (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between font-bold text-sm">
                  <span className="text-neutral-800">시장 변동성</span>
                      <span className={info.textColor}>{info.label}</span>
                    </div>
                    <div className="h-2.5 w-full rounded-full bg-neutral-200 overflow-hidden">
                      <div className={`h-full ${info.barColor} transition-all duration-500 rounded-full`} style={{ width: `${info.widthPercent}%` }} />
                    </div>
                    <p className="text-neutral-500 text-xs leading-normal pt-0.5">
                      단기 등락률과 캔들 기반 변동폭, 부정 뉴스 비중을 함께 반영한 민감도입니다.
                    </p>
                  </div>
                );
              })()}

              {/* 실적 신뢰도 */}
              {(() => {
                const info = getRiskInfo(report.riskScores?.["실적신뢰도"] ?? 35);
                return (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between font-bold text-sm">
                  <span className="text-neutral-800">실적 신뢰도</span>
                      <span className={info.textColor}>{info.label}</span>
                    </div>
                    <div className="h-2.5 w-full rounded-full bg-neutral-200 overflow-hidden">
                      <div className={`h-full ${info.barColor} transition-all duration-500 rounded-full`} style={{ width: `${info.widthPercent}%` }} />
                    </div>
                    <p className="text-neutral-500 text-xs leading-normal pt-0.5">
                      영업이익률과 밸류에이션 지표를 기준으로 실적 체력의 안정성을 평가했습니다.
                    </p>
                  </div>
                );
              })()}

              {/* 경쟁 강도 */}
              {(() => {
                const info = getRiskInfo(report.riskScores?.["경쟁강도"] ?? 50);
                return (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between font-bold text-sm">
                  <span className="text-neutral-800">경쟁 강도</span>
                      <span className={info.textColor}>{info.label}</span>
                    </div>
                    <div className="h-2.5 w-full rounded-full bg-neutral-200 overflow-hidden">
                      <div className={`h-full ${info.barColor} transition-all duration-500 rounded-full`} style={{ width: `${info.widthPercent}%` }} />
                    </div>
                    <p className="text-neutral-500 text-xs leading-normal pt-0.5">
                      섹터 경쟁 강도와 최근 경쟁 관련 뉴스 흐름을 함께 반영했습니다.
                    </p>
                  </div>
                );
              })()}
            </div>
          </div>

          {/* 블록 4. 최신 관련 뉴스 */}
          <div className="rounded-2xl border border-neutral-200/80 bg-white p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 border-b border-neutral-100 pb-3">
              <Newspaper className="h-5 w-5 text-info" />
              <h4 className="font-bold text-neutral-950 text-base">4. 최신 관련 뉴스</h4>
            </div>

            {report.latestNews && report.latestNews.length > 0 ? (
              <div className="space-y-3">
                {report.latestNews.map((news) => {
                  return (
                    <a
                      key={news.id}
                      href={news.url ?? "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block rounded-xl bg-neutral-50 p-3.5 border border-neutral-100 hover:bg-neutral-100 transition"
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-[12px] text-neutral-500">{news.publisher} • {news.publishedAt}</span>
                      </div>
                      <h5 className="text-xs font-semibold text-neutral-800 line-clamp-2 leading-relaxed">
                        {news.title}
                      </h5>
                    </a>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-neutral-500">최신 뉴스를 불러오는 중입니다.</p>
            )}
          </div>

          {/* 블록 5. 동종 업계 비교 */}
          <div className="rounded-2xl border border-neutral-200/80 bg-white p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 border-b border-neutral-100 pb-3">
              <Scale className="h-5 w-5 text-info" />
              <h4 className="font-bold text-neutral-950 text-base">5. 동종 업계 비교</h4>
            </div>

            {/* 4개 지표 탭 */}
            <div className="flex gap-1.5 border-b border-neutral-100 pb-3 overflow-x-auto no-scrollbar">
              {[
                { id: "opm", label: "영업이익률" },
                { id: "per", label: "PER" },
                { id: "pbr", label: "PBR" },
                { id: "roe", label: "ROE" },
              ].map((tab) => (
                <Button
                  variant="text"
                  key={tab.id}
                  onClick={() => setPeerTab(tab.id as any)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-xl transition ${peerTab === tab.id
                      ? "bg-info text-white shadow-sm"
                      : "bg-neutral-100 text-neutral-500 hover:bg-neutral-200"
                    }`}
                >
                  {tab.label}
                </Button>
              ))}
            </div>

            <div className="space-y-3">
              {(() => {
                if (!report.peerComparison || report.peerComparison.length === 0) {
                  return <p className="text-xs text-neutral-500">동종 업계 비교 데이터를 불러오는 중입니다.</p>;
                }

                // 조회 중인 종목 최상단 고정 + 나머지 peer 내림차순 정렬
                const targetPeer = report.peerComparison.find((p) => p.name === stockName);
                const otherPeers = report.peerComparison
                  .filter((p) => p.name !== stockName)
                  .sort((a, b) => {
                    const valA = getPeerValue(a, peerTab) ?? -999999;
                    const valB = getPeerValue(b, peerTab) ?? -999999;
                    return valB - valA; // 내림차순
                  });

                const sortedList = targetPeer ? [targetPeer, ...otherPeers] : report.peerComparison;

                // 최대 절대값 산출 (막대 % 계산용)
                const validValues = sortedList
                  .map((p) => getPeerValue(p, peerTab))
                  .filter((v): v is number => v !== null && v !== undefined && !isNaN(v));
                const maxAbsVal = validValues.length > 0 ? Math.max(...validValues.map((v) => Math.abs(v))) : 1;

                return sortedList.map((peer, i) => {
                  const isCurrent = peer.name === stockName;
                  const rawVal = getPeerValue(peer, peerTab);
                  const formattedVal = formatPeerValue(rawVal, peerTab);
                  const hasData = rawVal !== null && rawVal !== undefined && !isNaN(rawVal);

                  const widthPercent =
                    hasData && maxAbsVal > 0
                      ? Math.min(100, Math.max(15, (Math.abs(rawVal!) / maxAbsVal) * 100))
                      : 0;

                  return (
                    <div key={i} className="flex items-center gap-3 text-xs">
                      <span className={`w-20 shrink-0 ${isCurrent ? "font-bold text-neutral-950" : "font-medium text-neutral-500"}`}>
                        {peer.name}
                      </span>

                      {hasData ? (
                        <div className="h-3.5 flex-1 rounded-full bg-neutral-100 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${isCurrent ? "bg-info" : "bg-neutral-500"
                              }`}
                            style={{ width: `${widthPercent}%` }}
                          />
                        </div>
                      ) : (
                        <div className="flex-1 flex items-center">
                          <span className="text-[12px] text-neutral-500 italic">데이터 없음</span>
                        </div>
                      )}

                      <span className={`w-16 shrink-0 text-right font-mono ${isCurrent ? "font-bold text-neutral-950" : "font-medium text-neutral-500"}`}>
                        {formattedVal}
                      </span>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
