import StockLiveSection from "@/features/stock-quote/StockLiveSection";
import { API_BASE_URL } from "@/shared/config/env";
import type { StockReport } from "@/entities/report/types";
import type { Stock } from "@/entities/stock/types";
import PageContainer from "@/shared/ui/PageContainer";
import WeeklySentimentWeather from "@/widgets/stock-weather/WeeklySentimentWeather";
import StockReportSummaryWidget from "@/features/report/StockReportSummaryWidget";

async function fetchReport(code: string): Promise<StockReport | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/reports/${code}`, { cache: "no-store" });
    if (!res.ok) return null;
    const body = await res.json();
    return body.data;
  } catch {
    return null;
  }
}

async function fetchStock(code: string): Promise<Stock | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/stocks/${code}`, { cache: "no-store" });
    if (!res.ok) return null;
    const body = await res.json();
    return body.data;
  } catch {
    return null;
  }
}

export default async function StockReportPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const [report, stock] = await Promise.all([fetchReport(code), fetchStock(code)]);
  const stockName = stock?.name ?? code;

  return (
    <PageContainer>
      <div className="flex flex-col gap-4 pb-8">
        <StockLiveSection
          stockCode={code}
          stockName={stockName}
          market={stock?.market === "KOSDAQ" ? "코스닥" : "코스피"}
        />

        <WeeklySentimentWeather stockCode={code} />

        <div>
          <StockReportSummaryWidget
            report={report}
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
