export interface MarketIndexMock {
  title: string;
  value: string;
  change: string;
  changePercent: string;
  isUp: boolean;
  investors: {
    personal: number;
    foreign: number;
    inst: number;
  };
}

export interface ExchangeRateMock {
  currency: string;
  value: string;
  changePercent: string;
  isUp: boolean;
}

export interface StockRankingMock {
  code: string;
  name: string;
  price: string;
  changePercent: string;
  isUp: boolean;
  logoBg: string;
  logoText: string;
  isFavorite?: boolean;
}

export const MOCK_INDICES: MarketIndexMock[] = [
  {
    title: "코스피(예상)",
    value: "6,597.95",
    change: "252.42",
    changePercent: "3.98%",
    isUp: true,
    investors: {
      personal: -31782,
      foreign: 27457,
      inst: 6157,
    },
  },
  {
    title: "코스닥(예상)",
    value: "859.05",
    change: "1.21",
    changePercent: "0.14%",
    isUp: true,
    investors: {
      personal: 3063,
      foreign: -1512,
      inst: -1483,
    },
  },
];

export const MOCK_EXCHANGE_RATES: ExchangeRateMock[] = [
  { currency: "원/엔", value: "888.90", changePercent: "0.33%", isUp: true },
  { currency: "원/유로", value: "1,634.35", changePercent: "0.33%", isUp: true },
  { currency: "원/달러", value: "1,385.20", changePercent: "0.15%", isUp: false },
];

export const MOCK_AI_ISSUE = {
  title: "국내 주요 이슈",
  text: "국내 증시가 외국인과 기관의 대규모 매수세에 힘입어 4% 이상 급등하며 매수 사이드카가 발동되는 등 강한 회복세를 보였습니다. 반도체 업종을 중심으로 매수세가 가파르게 유입되었습니다.",
  timestamp: "2026.08.12 15:00:52 기준",
};

// 5개 마스터 종목 정의 (삼성전자, SK하이닉스, 현대자동차, LG에너지솔루션, 한화오션)
const MASTER_STOCKS: StockRankingMock[] = [
  {
    code: "005930",
    name: "삼성전자",
    price: "72,300원",
    changePercent: "+2.41%",
    isUp: true,
    logoBg: "bg-blue-600",
    logoText: "SEC",
  },
  {
    code: "000660",
    name: "SK하이닉스",
    price: "183,900원",
    changePercent: "+5.54%",
    isUp: true,
    logoBg: "bg-red-500",
    logoText: "SK",
  },
  {
    code: "005380",
    name: "현대자동차",
    price: "245,000원",
    changePercent: "+3.15%",
    isUp: true,
    logoBg: "bg-blue-700",
    logoText: "HD",
  },
  {
    code: "373220",
    name: "LG에너지솔루션",
    price: "385,000원",
    changePercent: "-1.28%",
    isUp: false,
    logoBg: "bg-emerald-600",
    logoText: "LGE",
  },
  {
    code: "042660",
    name: "한화오션",
    price: "29,500원",
    changePercent: "+1.72%",
    isUp: true,
    logoBg: "bg-orange-500",
    logoText: "한화",
  },
];

export const MOCK_RANKINGS: Record<string, StockRankingMock[]> = {
  인기검색: [
    MASTER_STOCKS[0], // 삼성전자
    MASTER_STOCKS[1], // SK하이닉스
    MASTER_STOCKS[2], // 현대자동차
    MASTER_STOCKS[3], // LG에너지솔루션
    MASTER_STOCKS[4], // 한화오션
  ],
  상승률: [
    MASTER_STOCKS[1], // SK하이닉스 (+5.54%)
    MASTER_STOCKS[2], // 현대자동차 (+3.15%)
    MASTER_STOCKS[0], // 삼성전자 (+2.41%)
    MASTER_STOCKS[4], // 한화오션 (+1.72%)
    MASTER_STOCKS[3], // LG에너지솔루션 (-1.28%)
  ],
  하락률: [
    MASTER_STOCKS[3], // LG에너지솔루션 (-1.28%)
    MASTER_STOCKS[4], // 한화오션
    MASTER_STOCKS[0], // 삼성전자
    MASTER_STOCKS[2], // 현대자동차
    MASTER_STOCKS[1], // SK하이닉스
  ],
  거래대금: [
    MASTER_STOCKS[0], // 삼성전자
    MASTER_STOCKS[1], // SK하이닉스
    MASTER_STOCKS[3], // LG에너지솔루션
    MASTER_STOCKS[2], // 현대자동차
    MASTER_STOCKS[4], // 한화오션
  ],
  거래량: [
    MASTER_STOCKS[0], // 삼성전자
    MASTER_STOCKS[4], // 한화오션
    MASTER_STOCKS[1], // SK하이닉스
    MASTER_STOCKS[2], // 현대자동차
    MASTER_STOCKS[3], // LG에너지솔루션
  ],
};
