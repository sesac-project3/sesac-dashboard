"use client";

import { useState } from "react";
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
  const [pending, setPending] = useState(false);
  const [popping, setPopping] = useState(false);

  const onClick = async () => {
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }
    if (pending) return;
    setPending(true);
    setPopping(true);
    setTimeout(() => setPopping(false), 200);
    try {
      const result = await toggleShortformLike(shortformId);
      setLiked(result.liked);
      setCount(result.likeCount);
    } catch {
      // ponytail: 토스트 없이 조용히 무시 — 재시도는 버튼 다시 누르면 됨
    } finally {
      setPending(false);
    }
  };

  // DESIGN_SPEC.md §26: right rail 아이콘 — 큰 아이콘 + 작은 label(카운트).
  return (
    <button
      onClick={onClick}
      disabled={pending}
      className="flex flex-col items-center gap-1 text-white"
      aria-label={liked ? "좋아요 취소" : "좋아요"}
    >
      <HeartIcon filled={liked} popping={popping} />
      <span className="text-[12px] font-medium">{count}</span>
    </button>
  );
}
