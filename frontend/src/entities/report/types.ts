export interface NewsItem {
  id: number;
  title: string;
  publisher: string;
  publishedAt: string;
  sentiment: "긍정" | "부정" | "중립";
  url?: string | null;
}

export interface FinancialRow {
  fiscalYear: number;
  revenue: number;
  operatingProfit: number;
  operatingMargin: number;
}

export interface PeerComparisonRow {
  name: string;
  per: number;
  pbr: number;
  roe: number;
  operating_margin?: number | null;
  operatingMargin?: number | null;
}

// PRD F-03 AI 심층 분석 리포트 데이터 모델
export interface StockReport {
  stockCode: string;
  reportDate: string;
  judgement: "BUY" | "HOLD" | "SELL" | "매수" | "중립" | "매도" | null;
  qualitativeSignal?: string | null;
  investmentSummary?: string | null;
  judgementReasons?: string[] | null;
  revenueTrend?: "증가" | "감소" | null;
  operatingProfitTrend?: "증가" | "감소" | null;
  operatingMarginTrend?: "개선" | "악화" | null;
  growthGrade?: "양호" | "보통" | "낮음" | null;
  profitabilityGrade?: "양호" | "보통" | "낮음" | null;
  financials?: FinancialRow[] | null;
  latestNews?: NewsItem[] | null;
  riskScores?: Record<string, number> | null;
  peerComparison?: PeerComparisonRow[] | null;
  week52High?: number | null;
  week52Low?: number | null;
  currentPrice?: number | null;
  valuationComment?: string | null;
}
