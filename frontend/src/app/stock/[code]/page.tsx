import StockLiveSection from "@/features/stock-quote/StockLiveSection";
import type { StockReport } from "@/entities/report/types";
import type { Stock } from "@/entities/stock/types";
import PageContainer from "@/shared/ui/PageContainer";
import WeeklySentimentWeather from "@/widgets/stock-weather/WeeklySentimentWeather";
import StockReportSummaryWidget from "@/features/report/StockReportSummaryWidget";
import { getStock } from "@/shared/api/stocks";
import { getStockReport } from "@/shared/api/reports";

type FetchResult<T> = { data: T | null; hasError: boolean };

async function fetchReport(code: string): Promise<FetchResult<StockReport>> {
  try {
    return { data: await getStockReport(code), hasError: false };
  } catch {
    return { data: null, hasError: true };
  }
}

async function fetchStock(code: string): Promise<FetchResult<Stock>> {
  try {
    return { data: await getStock(code), hasError: false };
  } catch {
    return { data: null, hasError: true };
  }
}

export default async function StockReportPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const [reportResult, stockResult] = await Promise.all([fetchReport(code), fetchStock(code)]);
  if (stockResult.hasError || !stockResult.data) {
    throw new Error("종목 정보를 불러오지 못했습니다.");
  }

  const stock = stockResult.data;
  const stockName = stock.name;

  return (
    <PageContainer>
      <div className="flex flex-col gap-4 pb-8">
        <StockLiveSection
          stockCode={code}
          stockName={stockName}
          market={stock?.market === "KOSDAQ" ? "KOSDAQ" : "KOSPI"}
        />

        <WeeklySentimentWeather stockCode={code} />

        <div>
          <StockReportSummaryWidget
            report={reportResult.data}
            reportError={reportResult.hasError}
            stockName={stockName}
            stockCode={code}
          />
        </div>

        <p className="px-5 text-center text-[12px] leading-[1.5] text-caption">
          본 정보는 투자 참고 자료이며 투자 권유가 아닙니다.
          <br />
          투자 판단과 그 결과에 대한 책임은 이용자 본인에게 있습니다.
        </p>
      </div>
    </PageContainer>
  );
}
