"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toggleShortformLike } from "@/shared/api/shortforms";
import { getAccessToken } from "@/shared/api/base";

// 인스타그램 스타일: 평소엔 흰색 outline 하트, 좋아요 누르면 빨간 채움 하트 + 살짝 튀는(pop)
// 스케일 애니메이션. DESIGN_SPEC.md 410행 "active favorite: red 계열" 규칙 적용.
function HeartIcon({ filled, popping }: { filled: boolean; popping: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={`h-7 w-7 drop-shadow transition-transform duration-200 ease-out ${
        popping ? "scale-125" : "scale-100"
      } ${filled ? "text-red-500" : "text-white"}`}
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={filled ? 0 : 1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
    </svg>
  );
}

export default function LikeButton({
  shortformId,
  initialLiked = false,
  initialCount,
}: {
  shortformId: number;
  initialLiked?: boolean;
  initialCount: number;
}) {
  const router = useRouter();
  const [liked, setLiked] = useState(initialLiked);
  const [count, setCount] = useState(initialCount);
  const [popping, setPopping] = useState(false);
  // 서버 응답을 기다리는 동안에도 리렌더를 더 유발하지 않도록 ref로 진행 중 요청을 추적.
  const inFlight = useRef(false);

  // 낙관적 업데이트: 서버 응답 기다리지 않고 하트/카운트를 바로 바꾸고, 실제 토글은
  // 백그라운드에서 처리한다. 실패했을 때만 원래 값으로 되돌린다(관심종목 하트와 동일 패턴).
  const onClick = () => {
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }

    setPopping(true);
    setTimeout(() => setPopping(false), 200);

    const previousLiked = liked;
    const previousCount = count;
    const nextLiked = !previousLiked;
    setLiked(nextLiked);
    setCount(previousCount + (nextLiked ? 1 : -1));

    if (inFlight.current) return; // 같은 버튼에 이미 요청이 나가 있으면 낙관적 표시만 갱신
    inFlight.current = true;
    toggleShortformLike(shortformId)
      .then((result) => {
        setLiked(result.liked);
        setCount(result.likeCount);
      })
      .catch(() => {
        setLiked(previousLiked);
        setCount(previousCount);
      })
      .finally(() => {
        inFlight.current = false;
      });
  };

  // DESIGN_SPEC.md §26: right rail 아이콘 — 큰 아이콘 + 작은 label(카운트).
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-1 text-white"
      aria-label={liked ? "좋아요 취소" : "좋아요"}
    >
      <HeartIcon filled={liked} popping={popping} />
      <span className="text-[12px] font-medium">{count}</span>
    </button>
  );
}
