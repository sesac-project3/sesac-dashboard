"use client";

import { useCallback, useState } from "react";
import type { Shortform } from "@/entities/shortform/types";
import ShortformCard from "@/widgets/shortform-feed/ShortformCard";

const INITIAL_BATCH = 5;
const BATCH_SIZE = 5;
// 배치 끝에서 2개 남았을 때(=5개짜리 배치의 4번째 영상) 다음 배치를 미리 풀어준다.
const TRIGGER_FROM_END = 2;

export default function ShortformFeed({ shortforms }: { shortforms: Shortform[] }) {
  const [loadedCount, setLoadedCount] = useState(() => Math.min(INITIAL_BATCH, shortforms.length));

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
    <div className="h-full snap-y snap-mandatory overflow-y-scroll overscroll-y-contain">
      {shortforms.map((sf, index) => (
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
