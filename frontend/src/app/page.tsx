import { API_BASE_URL } from "@/shared/config/env";
import type { MarketIndex } from "@/entities/stock/types";

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
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">오늘의 시장</h1>
      <div className="grid grid-cols-3 gap-3">
        {(indices ?? []).map((index) => (
          <div key={index.indexType} className="rounded-lg border border-black/10 p-3">
            <p className="text-xs text-black/60">{LABELS[index.indexType]}</p>
            <p className="text-base font-semibold">{index.value.toLocaleString()}</p>
          </div>
        ))}
        {!indices && (
          <p className="col-span-3 text-sm text-black/50">
            시세를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
          </p>
        )}
      </div>
    </div>
  );
}
