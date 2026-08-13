"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { Sparkles, Volume2, VolumeX } from "lucide-react";
import type { Shortform } from "@/entities/shortform/types";
import LikeButton from "@/features/shortform-like/LikeButton";
import { getResumePosition, saveVideoPosition } from "@/widgets/shortform-feed/videoPositionStore";
import { getServerSnapshot, getSnapshot, setMuted, setVolume, subscribe } from "@/widgets/shortform-feed/volumeStore";

const SENTIMENT_GRADIENT: Record<Shortform["sentiment"], string> = {
  POS: "from-rose-500 to-orange-400",
  NEG: "from-slate-700 to-slate-900",
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
  // 영상 자체(첫 프레임)가 아직 준비 안 됐을 때 보여줄 스켈레톤 — 영상이 없는 카드(정적
  // 배경 폴백)는 기다릴 게 없으니 처음부터 true.
  const [videoReady, setVideoReady] = useState(!shortform.videoUrl);
  // 볼륨/음소거는 이 카드만의 상태가 아니라 전체 숏폼 피드가 공유하는 값이다(다음 영상으로
  // 스크롤해도 유지돼야 하므로) — useSyncExternalStore로 모듈 스코프 store를 구독한다.
  const { volume, muted: isMuted } = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const toggleInsight = () => setShowInsight((v) => !v);
  const insightLines = shortform.aiInsight?.split("\n").filter(Boolean) ?? [];

  const videoRef = useRef<HTMLVideoElement>(null);
  const leftViewAtRef = useRef<number | null>(null);

  // <video>의 volume은 HTML 속성이 아니라 DOM 프로퍼티라 JSX로 못 넘긴다 — ref로 직접 설정.
  useEffect(() => {
    if (videoRef.current) videoRef.current.volume = volume;
  }, [volume]);

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

          if (leftViewAtRef.current === null) {
            // 이 컴포넌트 인스턴스에서 처음 화면에 들어온 순간 — 같은 피드 안에서
            // 스크롤하다 돌아온 게 아니라, 다른 탭 갔다가 돌아와서 방금 새로 마운트됐을
            // 수도 있다. 그 경우 모듈 스코프 저장소에 10초 이내 위치가 있으면 이어서.
            const resumeAt = getResumePosition(shortform.id);
            video.currentTime = resumeAt ?? 0;
          } else {
            const awayMs = Date.now() - leftViewAtRef.current;
            if (awayMs >= RESET_AFTER_MS) {
              video.currentTime = 0;
            }
          }

          video.play().catch(() => {
            // 브라우저 자동재생 정책으로 막힐 수 있음 — 사용자가 탭하면 어차피 토글되니 무시
          });
        } else {
          video.pause();
          leftViewAtRef.current = Date.now();
          // currentTime===0이면 저장할 만한 게 없다 — 그보다 중요한 건, 마운트 직후
          // IntersectionObserver가 레이아웃이 채 안 잡힌 상태에서 isIntersecting:false를
          // 한 번 먼저 쏘는 경우가 있는데(브라우저 표준 동작), 그때 0으로 덮어쓰면
          // 방금 복귀 로직이 읽으려던 "10초 이내 저장값"이 통째로 날아간다.
          if (video.currentTime > 0) {
            saveVideoPosition(shortform.id, video.currentTime);
          }
        }
      },
      { threshold: 0.6 },
    );
    observer.observe(video);

    // 탭 이동은 페이지/컴포넌트가 통째로 언마운트되면서 일어난다 — 그 순간에도
    // 마지막 위치를 저장해둬야 "10초 안에 돌아오면 이어서"가 성립한다.
    return () => {
      observer.disconnect();
      if (video.currentTime > 0) {
        saveVideoPosition(shortform.id, video.currentTime);
      }
    };
  }, [shortform.id]);

  return (
    <article className="relative h-full w-full overflow-hidden bg-black text-white">
      {shortform.videoUrl ? (
        <video
          ref={videoRef}
          src={shortform.videoUrl}
          onClick={toggleInsight}
          onLoadedData={() => setVideoReady(true)}
          className={`h-full w-full cursor-pointer object-cover transition-opacity duration-300 ${
            videoReady ? "opacity-100" : "opacity-0"
          }`}
          // preload="auto": 기본값(metadata)이면 브라우저가 play()를 부를 때가 돼서야
          // 본편을 받기 시작해서, 큰 영상으로 스크롤해 오면 그때 랙이 걸린다. 배치 윈도우
          // 밖(preload=false)인 카드는 "none"으로 둬서 아직 안 쓸 영상까지 미리 받아
          // 대역폭을 낭비하지 않는다 — 배치 확장은 ShortformFeed가 담당.
          preload={preload ? "auto" : "none"}
          loop
          muted={isMuted}
          playsInline
        />
      ) : (
        // ISSUE-E3(영상 합성) 전까지는 정적 배경으로 폴백 (PRODUCT.md §6)
        <div
          onClick={toggleInsight}
          className={`h-full w-full cursor-pointer bg-gradient-to-br ${SENTIMENT_GRADIENT[shortform.sentiment]}`}
        />
      )}

      {/* 영상 첫 프레임 로딩 중 스켈레톤 — 홈/관심종목과 같은 animate-pulse + bg-surface 패턴 */}
      {!videoReady && (
        <div
          className="pointer-events-none absolute inset-0 animate-pulse bg-surface"
          aria-label="영상을 불러오는 중"
          aria-busy="true"
        />
      )}

      {/* 리포트 요약 자막 — 영상 정중앙, 굵은 흰 글씨 + 검정 테두리(자막 밈 스타일).
          지금은 데모라 aiInsight 첫 줄을 그대로 씀(이미 whisper+LLM으로 만든 실 데이터,
          가짜 수치 아님) — 나중에 OpenAI로 리포트 요약을 따로 생성하면 그 결과로 교체.
          article의 자식이라 카드가 스크롤될 때 영상과 같이 그 위치에서 이동한다(별도 처리 불필요). */}
      <div className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 px-6 text-center">
        <p
          className="text-2xl leading-snug font-extrabold text-white"
          style={{
            textShadow:
              "-2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0 2px 8px rgba(0,0,0,0.4)",
          }}
        >
          {insightLines[0] ?? "AI 리포트 요약 준비 중"}
        </p>
      </div>

      {/* 상단: 종목/감성 배지 + AI INSIGHT 토글 버튼 (영상을 탭해도 같은 토글이 열림) */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between p-3">
        <span className="rounded-full bg-black/40 px-2 py-1 text-xs">
          {shortform.stockName} ·{" "}
          <span className={shortform.sentiment === "POS" ? "text-market-up" : "text-market-down"}>
            {shortform.sentiment}
          </span>
        </span>
        <div className="flex items-center gap-2">
          {/* 볼륨 조절 — AI INSIGHT 버튼 왼쪽에 배치. 슬라이더 값은 피드 전체가 공유하는
              store라 다음 영상으로 넘어가도 그대로 유지된다. */}
          <div
            className="pointer-events-auto flex items-center gap-1.5 px-2 py-1"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setMuted(!isMuted)}
              className="flex items-center justify-center text-white"
              aria-label={isMuted ? "음소거 해제" : "음소거"}
              title={isMuted ? "음소거 해제" : "음소거"}
            >
              {isMuted || volume === 0 ? (
                <VolumeX className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Volume2 className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={isMuted ? 0 : volume}
              onChange={(e) => setVolume(Number(e.target.value))}
              className="volume-slider h-1 w-14"
              style={{ accentColor: "white" }}
              aria-label="볼륨 조절"
            />
          </div>
          {insightLines.length > 0 && (
            <button
              onClick={toggleInsight}
              // 데스크톱: 마우스 올리면 미리보기로 뜨고 떼면 사라짐(호버). 탭/클릭은 그대로
              // 토글이라 터치 기기(호버 없음)에서도 동일하게 동작한다.
              onMouseEnter={() => setShowInsight(true)}
              onMouseLeave={() => setShowInsight(false)}
              className={`pointer-events-auto rounded-full px-2.5 py-1 text-sm font-medium transition-colors ${
                showInsight ? "bg-primary text-white" : "bg-black/40 text-white"
              }`}
            >
              <Sparkles className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" /> AI INSIGHT
            </button>
          )}
        </div>
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
          <Sparkles className="mr-1 inline h-3 w-3" aria-hidden="true" /> AI INSIGHT
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

      {/* DESIGN_SPEC.md §26: interaction icon은 right rail로 세로 배치.
          음소거/볼륨 조절은 상단 바(AI INSIGHT 왼쪽)로 옮겨서 여긴 좋아요만 남는다. */}
      <div className="pointer-events-auto absolute right-3 bottom-[312px] flex flex-col items-center gap-5">
        <LikeButton
          shortformId={shortform.id}
          initialLiked={shortform.liked}
          initialCount={shortform.likeCount}
        />
      </div>

      {/* 하단: 종목명/자막(캡션) + CTA — 자막은 접근성 위해 항상 텍스트로 노출 (PRD §8) */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-col gap-3 bg-gradient-to-t from-black/80 to-transparent p-4 pb-6">
        <div className="pointer-events-auto rounded-xl bg-black/50 px-3 py-2 backdrop-blur-[2px]">
          <p className="text-[18px] font-semibold text-white/80">
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
