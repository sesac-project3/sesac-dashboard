// PRD F-03 6개 블록. 근거 없으면 judgement가 null → 프론트에서 해당 블록 비노출.
export interface StockReport {
  stockCode: string;
  reportDate: string;
  judgement: "매수" | "중립" | "매도" | null;
  judgementReasons: string[] | null;
  revenueTrend: "증가" | "감소" | null;
  operatingProfitTrend: "증가" | "감소" | null;
  growthGrade: "양호" | "보통" | "낮음" | null;
  riskScores: Record<string, number> | null;
  peerComparison: Array<{ name: string; per: number; pbr: number; roe: number }> | null;
  week52High: number | null;
  week52Low: number | null;
  currentPrice: number | null;
}
