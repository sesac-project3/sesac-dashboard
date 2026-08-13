"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Shortform } from "@/entities/shortform/types";
import ShortformCard from "@/widgets/shortform-feed/ShortformCard";
import { getAccessToken } from "@/shared/api/base";
import { getLikedShortformIds } from "@/shared/api/shortforms";

const INITIAL_BATCH = 5;
const BATCH_SIZE = 5;
// 배치 끝에서 2개 남았을 때(=5개짜리 배치의 4번째 영상) 다음 배치를 미리 풀어준다.
const TRIGGER_FROM_END = 2;

export default function ShortformFeed({ shortforms }: { shortforms: Shortform[] }) {
  const [loadedCount, setLoadedCount] = useState(() => Math.min(INITIAL_BATCH, shortforms.length));
  const [likedIds, setLikedIds] = useState<Set<number> | null>(null);

  // shortforms 목록 자체(subtitle/영상/카운트 등)는 서버 컴포넌트가 캐시 걸어 가져오는
  // 공유 데이터라 liked는 항상 false로 온다 — 로그인했으면 내 좋아요 목록만 클라이언트에서
  // 따로 가져와 합친다(shared/api/shortforms.ts 주석 참고).
  useEffect(() => {
    if (!getAccessToken()) return;
    getLikedShortformIds()
      .then((ids) => setLikedIds(new Set(ids)))
      .catch(() => {
        // ponytail: 실패하면 그냥 서버가 준 값(전부 false)대로 둔다 — 좋아요 버튼을
        // 눌러보면 실제 상태로 다시 맞춰짐
      });
  }, []);

  const mergedShortforms = useMemo(() => {
    if (likedIds === null) return shortforms;
    return shortforms.map((sf) => (likedIds.has(sf.id) ? { ...sf, liked: true } : sf));
  }, [shortforms, likedIds]);

  // index번째 영상이 재생될 때 호출됨. 함수형 업데이트로 최신 loadedCount를 기준으로
  // 판단해서, onVisible이 매 렌더 새로 만들어지는 함수여도(ShortformCard 쪽 ref 패턴과
  // 별개로) 클로저가 낡은 loadedCount를 참조하는 문제가 없다.
  const handleActive = useCallback(
    (index: number) => {
      setLoadedCount((prev) => {
        if (prev >= shortforms.length) return prev;
        if (index < prev - TRIGGER_FROM_END) return prev;
        return Math.min(shortforms.length, prev + BATCH_SIZE);
      });
    },
    [shortforms.length],
  );

  return (
    <div className="no-scrollbar h-full snap-y snap-mandatory overflow-y-scroll overscroll-y-contain">
      {mergedShortforms.map((sf, index) => (
        <div key={sf.id} className="h-full w-full snap-start snap-always">
          <ShortformCard
            shortform={sf}
            preload={index < loadedCount}
            onVisible={() => handleActive(index)}
          />
        </div>
      ))}
    </div>
  );
}
