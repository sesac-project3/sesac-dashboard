"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Shortform } from "@/entities/shortform/types";
import LikeButton from "@/features/shortform-like/LikeButton";

const SENTIMENT_GRADIENT: Record<Shortform["sentiment"], string> = {
  긍정: "from-rose-500 to-orange-400",
  부정: "from-slate-700 to-slate-900",
};

export default function ShortformCard({
  shortform,
  preload = true,
  onVisible,
}: {
  shortform: Shortform;
  /** false면 브라우저가 본편을 미리 안 받는다 — ShortformFeed가 배치 윈도우 밖의 카드에 넘김 */
  preload?: boolean;
  /** 이 카드가 화면에 60% 이상 들어왔을 때 호출 — ShortformFeed가 다음 배치 로딩 트리거로 씀 */
  onVisible?: () => void;
}) {
  const [showInsight, setShowInsight] = useState(false);
  const toggleInsight = () => setShowInsight((v) => !v);
  const insightLines = shortform.aiInsight?.split("\n").filter(Boolean) ?? [];

  const videoRef = useRef<HTMLVideoElement>(null);
  const leftViewAtRef = useRef<number | null>(null);

  // onVisible은 부모(ShortformFeed)가 매 렌더마다 새로 만들어 넘기는 함수라, 아래 effect의
  // deps에 넣으면 IntersectionObserver를 매번 disconnect/재생성해야 한다. ref에 최신 값만
  // 담아두고 effect는 마운트 시 한 번만 구독하게 한다.
  const onVisibleRef = useRef(onVisible);
  onVisibleRef.current = onVisible;

  // 스크롤 피드에서 화면에 보이는 영상만 재생하고 나머진 멈춘다 — autoPlay만 걸어두면
  // 목록에 있는 영상이 전부 동시에 재생돼버린다 (소리는 muted라 안 들려도 CPU/대역폭 낭비).
  // 다른 영상 보다가 4초 이상 지나서 돌아오면 처음부터, 4초 안에 잠깐 왔다갔다한 거면
  // 보던 지점 그대로 이어서 재생한다.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const RESET_AFTER_MS = 4000;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          onVisibleRef.current?.();
          const awayMs = leftViewAtRef.current === null ? null : Date.now() - leftViewAtRef.current;
          if (awayMs === null || awayMs >= RESET_AFTER_MS) {
            video.currentTime = 0;
          }
          video.play().catch(() => {
            // 브라우저 자동재생 정책으로 막힐 수 있음 — 사용자가 탭하면 어차피 토글되니 무시
          });
        } else {
          video.pause();
          leftViewAtRef.current = Date.now();
        }
      },
      { threshold: 0.6 },
    );
    observer.observe(video);
    return () => observer.disconnect();
  }, []);

  return (
    <article className="relative h-full w-full overflow-hidden bg-black text-white">
      {shortform.videoUrl ? (
        <video
          ref={videoRef}
          src={shortform.videoUrl}
          onClick={toggleInsight}
          className="h-full w-full cursor-pointer object-cover"
          // preload="auto": 기본값(metadata)이면 브라우저가 play()를 부를 때가 돼서야
          // 본편을 받기 시작해서, 큰 영상으로 스크롤해 오면 그때 랙이 걸린다. 배치 윈도우
          // 밖(preload=false)인 카드는 "none"으로 둬서 아직 안 쓸 영상까지 미리 받아
          // 대역폭을 낭비하지 않는다 — 배치 확장은 ShortformFeed가 담당.
          preload={preload ? "auto" : "none"}
          loop
          muted
          playsInline
        />
      ) : (
        // ISSUE-E3(영상 합성) 전까지는 정적 배경으로 폴백 (PRODUCT.md §6)
        <div
          onClick={toggleInsight}
          className={`h-full w-full cursor-pointer bg-gradient-to-br ${SENTIMENT_GRADIENT[shortform.sentiment]}`}
        />
      )}

      {/* 상단: 종목/감성 배지 + AI INSIGHT 토글 버튼 (영상을 탭해도 같은 토글이 열림) */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between p-3">
        <span className="rounded-full bg-black/40 px-2 py-1 text-xs">
          {shortform.stockName} ·{" "}
          <span className={shortform.sentiment === "긍정" ? "text-market-up" : "text-market-down"}>
            {shortform.sentiment}
          </span>
        </span>
        {insightLines.length > 0 && (
          <button
            onClick={toggleInsight}
            className={`pointer-events-auto rounded-full px-2 py-1 text-xs font-medium transition-colors ${
              showInsight ? "bg-primary text-white" : "bg-black/40 text-white"
            }`}
          >
            ✨ AI INSIGHT
          </button>
        )}
      </div>

      {/* z-invest 프로토타입: 영상 위에 탭하면 뜨는 AI INSIGHT 패널 (핵심 포인트 3줄, PRD 시나리오 A) */}
      <div
        className={`absolute inset-x-0 top-0 flex h-full flex-col justify-center bg-black/75 p-6 backdrop-blur-sm transition-all duration-300 ease-out ${
          showInsight
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none translate-y-2 opacity-0"
        }`}
        onClick={toggleInsight}
      >
        <p className="mb-3 text-xs font-semibold tracking-wide text-white/60">
          ✨ AI INSIGHT
        </p>
        <ul className="space-y-3">
          {insightLines.map((line, i) => (
            <li key={i} className="flex items-start gap-2 text-base leading-snug">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-white/70" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
        <p className="mt-6 text-xs text-white/40">탭하면 닫혀요</p>
      </div>

      {/* DESIGN_SPEC.md §26: interaction icon은 right rail로 세로 배치 */}
      <div className="pointer-events-auto absolute right-3 bottom-28 flex flex-col items-center gap-5">
        <LikeButton shortformId={shortform.id} initialCount={shortform.likeCount} />
      </div>

      {/* 하단: 종목명/자막(캡션) + CTA — 자막은 접근성 위해 항상 텍스트로 노출 (PRD §8) */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-col gap-3 bg-gradient-to-t from-black/80 to-transparent p-4 pb-6">
        <div className="pointer-events-auto">
          <p className="text-[13px] font-semibold text-white/80">
            {shortform.stockName} · {shortform.stockCode}
          </p>
          <p className="mt-1 text-[14px] leading-[1.5]">{shortform.subtitleText}</p>
        </div>
        <Link
          href={`/stock/${shortform.stockCode}`}
          className="pointer-events-auto flex h-[52px] w-full items-center justify-center rounded-full bg-primary text-[15px] font-medium text-white transition active:scale-[0.98]"
        >
          종목 분석 보기
        </Link>
      </div>
    </article>
  );
}
