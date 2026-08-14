import type { Shortform } from "@/entities/shortform/types";
import ShortformFeed from "@/widgets/shortform-feed/ShortformFeed";
import { getShortforms } from "@/shared/api/shortforms";

async function fetchShortforms(): Promise<Shortform[]> {
  try {
    return await getShortforms();
  } catch {
    return [];
  }
}

export default async function ShortformPage() {
  const shortforms = await fetchShortforms();

  if (shortforms.length === 0) {
    return (
      <div className="p-4">
        <h1 className="mb-4 text-[18px] font-semibold text-heading">숏폼</h1>
        <p className="text-[14px] text-caption">아직 준비된 영상이 없습니다.</p>
      </div>
    );
  }

  // 세로 스크롤 = 다음/이전 영상 (PRD 시나리오 A: "아래로 스크롤하면 다음 영상이 이어진다").
  // snap-mandatory + snap-always는 CSS만으로 휠/트랙패드/터치 스와이프를 한 화면씩 딱딱 넘긴다.
  // 배치 단위 프리로드(초기 5개 → 4번째 재생 시 다음 5개)는 ShortformFeed가 담당.
  return <ShortformFeed shortforms={shortforms} />;
}
