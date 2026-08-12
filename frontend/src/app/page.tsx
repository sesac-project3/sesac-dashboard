import Link from "next/link";
import { API_BASE_URL } from "@/shared/config/env";
import type { MarketIndex } from "@/entities/stock/types";
import PageContainer from "@/shared/ui/PageContainer";
import StatCard from "@/shared/ui/StatCard";

async function fetchIndices(): Promise<MarketIndex[] | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/stocks/market/indices`, {
      next: { revalidate: 30 },
    });
    if (!res.ok) return null;
    const body = await res.json(); // ApiResponse 봉투: { data: MarketIndex[], ... }
    return body.data;
  } catch {
    // PRD §8: 외부 API/백엔드 장애 시 빈 화면 대신 마지막 상태를 안내
    return null;
  }
}

const LABELS: Record<MarketIndex["indexType"], string> = {
  KOSPI: "코스피",
  KOSDAQ: "코스닥",
  USD_KRW: "원/달러",
};

export default async function HomePage() {
  const indices = await fetchIndices();

  return (
    <PageContainer>
      <h1 className="py-6 text-[18px] font-semibold text-heading">오늘의 시장</h1>

      {indices ? (
        <div className="grid grid-cols-3 gap-3">
          {indices.map((index) => (
            <StatCard
              key={index.indexType}
              label={LABELS[index.indexType]}
              value={index.value.toLocaleString()}
            />
          ))}
        </div>
      ) : (
        // DESIGN_SPEC.md §23.3 Error state
        <div className="flex flex-col items-center gap-4 rounded-lg border border-border-soft bg-white py-12 text-center shadow-card">
          <p className="text-[14px] text-caption">
            데이터를 불러오지 못했어요.
            <br />
            잠시 후 다시 시도해주세요.
          </p>
          <Link
            href="/"
            className="rounded-sm bg-primary px-5 py-2.5 text-[14px] font-medium text-white active:scale-[0.98]"
          >
            다시 시도
          </Link>
        </div>
      )}
    </PageContainer>
  );
}
