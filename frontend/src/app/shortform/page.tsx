import { API_BASE_URL } from "@/shared/config/env";
import type { Shortform } from "@/entities/shortform/types";
import ShortformFeed from "@/widgets/shortform-feed/ShortformFeed";

async function fetchShortforms(): Promise<Shortform[]> {
  try {
    // cache: "no-store"면 페이지 이동/새로고침마다 백엔드를 다시 타고, 백엔드도 매번
    // S3 head_object를 다시 부른다(비록 Redis 덕분에 URL 자체는 같아도). 홈 대시보드와
    // 같은 방식(revalidate)으로 캐싱해서 초기 로딩을 줄인다 — 좋아요 수 등은 최대
    // 30초 정도 늦게 반영될 수 있지만, 숏폼 피드에서는 감내할 만한 트레이드오프.
    const res = await fetch(`${API_BASE_URL}/shortforms`, { next: { revalidate: 30 } });
    if (!res.ok) return [];
    const body = await res.json(); // ApiResponse 봉투
    return body.data ?? [];
  } catch {
    return [];
  }
}

export default async function ShortformPage() {
  const shortforms = await fetchShortforms();

  if (shortforms.length === 0) {
    return (
      <div className="p-4">
        <h1 className="mb-4 text-lg font-semibold">숏폼</h1>
        <p className="text-sm text-black/50">아직 준비된 영상이 없습니다.</p>
      </div>
    );
  }

  // 세로 스크롤 = 다음/이전 영상 (PRD 시나리오 A: "아래로 스크롤하면 다음 영상이 이어진다").
  // snap-mandatory + snap-always는 CSS만으로 휠/트랙패드/터치 스와이프를 한 화면씩 딱딱 넘긴다.
  // 배치 단위 프리로드(초기 5개 → 4번째 재생 시 다음 5개)는 ShortformFeed가 담당.
  return <ShortformFeed shortforms={shortforms} />;
}
