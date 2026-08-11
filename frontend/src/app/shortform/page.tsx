import { API_BASE_URL } from "@/shared/config/env";
import type { Shortform } from "@/entities/shortform/types";

async function fetchShortforms(): Promise<Shortform[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/shortforms`, { cache: "no-store" });
    if (!res.ok) return [];
    const body = await res.json(); // ApiResponse 봉투
    return body.data ?? [];
  } catch {
    return [];
  }
}

export default async function ShortformPage() {
  const shortforms = await fetchShortforms();

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-lg font-semibold">숏폼</h1>
      {shortforms.length === 0 && (
        <p className="text-sm text-black/50">아직 준비된 영상이 없습니다.</p>
      )}
      {shortforms.map((sf) => (
        <a
          key={sf.id}
          href={`/stock/${sf.stockCode}`}
          className="rounded-lg border border-black/10 p-3"
        >
          <p className="text-xs text-black/60">
            {sf.stockName} · {sf.sentiment}
          </p>
          <p className="mt-1 text-sm">{sf.aiInsight}</p>
        </a>
      ))}
    </div>
  );
}
