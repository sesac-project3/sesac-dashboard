import { API_BASE_URL } from "@/shared/config/env";
import type { Shortform } from "@/entities/shortform/types";
import PageContainer from "@/shared/ui/PageContainer";
import Card from "@/shared/ui/Card";

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

// NOTE: 실제 풀스크린 비디오 피드(ShortformCard/ShortformFeed, 스크롤 스냅, S3 배경 영상)는
// feat/shortform-stt 브랜치에 아직 안 머지된 상태라 이 브랜치엔 없다. DESIGN_SPEC.md §26의
// 풀스크린 비디오 카드 디자인은 그 브랜치가 머지된 뒤 적용해야 중복 작업/충돌이 안 생긴다.
// 지금은 그때까지 화면이 완전히 깨져 보이지 않도록 토큰만 가볍게 입혀둔다.
export default async function ShortformPage() {
  const shortforms = await fetchShortforms();

  return (
    <PageContainer>
      <h1 className="py-6 text-[18px] font-semibold text-heading">숏폼</h1>

      {shortforms.length === 0 && (
        <p className="text-center text-[14px] text-caption">아직 준비된 영상이 없습니다.</p>
      )}

      <div className="flex flex-col gap-3 pb-8">
        {shortforms.map((sf) => (
          <a key={sf.id} href={`/stock/${sf.stockCode}`}>
            <Card>
              <p className="text-[13px] text-caption">
                {sf.stockName} ·{" "}
                <span className={sf.sentiment === "긍정" ? "text-market-up" : "text-market-down"}>
                  {sf.sentiment}
                </span>
              </p>
              <p className="mt-1 text-[14px] text-heading">{sf.aiInsight}</p>
            </Card>
          </a>
        ))}
      </div>
    </PageContainer>
  );
}
