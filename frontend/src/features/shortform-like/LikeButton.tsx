"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toggleShortformLike } from "@/shared/api/shortforms";
import { getAccessToken } from "@/shared/api/base";

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

  const onClick = async () => {
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }
    if (pending) return;
    setPending(true);
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

  return (
    <button
      onClick={onClick}
      disabled={pending}
      className={`flex items-center gap-1 rounded-full px-3 py-1 text-sm ${
        liked ? "bg-red-500 text-white" : "bg-white/20 text-white"
      }`}
    >
      {liked ? "❤️" : "🤍"} {count}
    </button>
  );
}
