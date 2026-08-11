"use client";

import { useState } from "react";
import Link from "next/link";
import type { Shortform } from "@/entities/shortform/types";
import LikeButton from "@/features/shortform-like/LikeButton";

const SENTIMENT_GRADIENT: Record<Shortform["sentiment"], string> = {
  긍정: "from-rose-500 to-orange-400",
  부정: "from-slate-700 to-slate-900",
};

export default function ShortformCard({ shortform }: { shortform: Shortform }) {
  const [showInsight, setShowInsight] = useState(false);

  return (
    <article className="relative aspect-[9/16] w-full overflow-hidden rounded-2xl bg-black text-white">
      {shortform.videoUrl ? (
        <video
          src={shortform.videoUrl}
          className="h-full w-full object-cover"
          autoPlay
          loop
          muted
          playsInline
        />
      ) : (
        // ISSUE-E3(영상 합성) 전까지는 정적 배경으로 폴백 (PRODUCT.md §6)
        <div
          className={`h-full w-full bg-gradient-to-br ${SENTIMENT_GRADIENT[shortform.sentiment]}`}
        />
      )}

      {/* 상단: 종목/감성 배지 + AI INSIGHT 토글 */}
      <div className="absolute inset-x-0 top-0 flex items-center justify-between p-3">
        <span className="rounded-full bg-black/40 px-2 py-1 text-xs">
          {shortform.stockName} · {shortform.sentiment}
        </span>
        {shortform.aiInsight && (
          <button
            onClick={() => setShowInsight((v) => !v)}
            className="rounded-full bg-black/40 px-2 py-1 text-xs"
          >
            AI INSIGHT
          </button>
        )}
      </div>

      {showInsight && shortform.aiInsight && (
        <div className="absolute inset-x-3 top-12 rounded-lg bg-black/70 p-3 text-xs leading-relaxed whitespace-pre-line">
          {shortform.aiInsight}
        </div>
      )}

      {/* 하단: 자막(캡션) + 좋아요 + CTA — 자막은 접근성 위해 항상 텍스트로 노출 (PRD §8) */}
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-2 bg-gradient-to-t from-black/80 to-transparent p-3">
        <p className="text-sm">{shortform.subtitleText}</p>
        <div className="flex items-center justify-between">
          <LikeButton
            shortformId={shortform.id}
            initialCount={shortform.likeCount}
          />
          <Link
            href={`/stock/${shortform.stockCode}`}
            className="rounded-full bg-white px-3 py-1 text-sm font-medium text-black"
          >
            종목 분석 보기
          </Link>
        </div>
      </div>
    </article>
  );
}
