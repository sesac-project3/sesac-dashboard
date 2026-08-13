export interface ExchangeRateMock {
  currency: string;
  value: string;
  changePercent: string;
  isUp: boolean;
}

export const MOCK_EXCHANGE_RATES: ExchangeRateMock[] = [
  { currency: "원/엔", value: "888.90", changePercent: "0.33%", isUp: true },
  { currency: "원/유로", value: "1,634.35", changePercent: "0.33%", isUp: true },
  { currency: "원/달러", value: "1,385.20", changePercent: "0.15%", isUp: false },
];

// AI 이슈 요약은 이번 KIS 실데이터 연동 범위 밖이라 mock 유지.
export const MOCK_AI_ISSUE = {
  title: "국내 주요 이슈",
  text: "국내 증시가 외국인과 기관의 대규모 매수세에 힘입어 4% 이상 급등하며 매수 사이드카가 발동되는 등 강한 회복세를 보였습니다. 반도체 업종을 중심으로 매수세가 가파르게 유입되었습니다.",
  timestamp: "2026.08.12 15:00:52 기준",
};
