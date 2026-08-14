"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Play, Sparkles } from "lucide-react";

const SLIDES = [
  {
    headline: "코스피, 코스닥, 환율까지\n한 화면에서",
    description: "매일 아침, 오늘의 시장 상황을 가장 먼저 확인하세요.",
    illustration: (
      <div className="flex flex-col gap-3">
        {[
          { label: "코스피", value: "2,650.12", up: true },
          { label: "코스닥", value: "845.30", up: true },
          { label: "원/달러", value: "1,380.5", up: false },
        ].map((row) => (
          <div
            key={row.label}
            className="flex items-center justify-between rounded-full bg-white px-4 py-2 shadow-card"
          >
            <span className="text-[13px] text-caption">{row.label}</span>
            <span className={`text-[14px] font-bold ${row.up ? "text-market-up" : "text-market-down"}`}>
              {row.up ? <ArrowUp className="mr-1 inline h-3 w-3" aria-hidden="true" /> : <ArrowDown className="mr-1 inline h-3 w-3" aria-hidden="true" />} {row.value}
            </span>
          </div>
        ))}
      </div>
    ),
  },
  {
    headline: "스크롤 한 번으로\n오늘의 종목 이슈",
    description: "긍정·부정 뉴스를 숏폼으로 빠르게, AI 인사이트까지 함께.",
    illustration: (
      <div className="relative mx-auto flex h-full w-[120px] flex-col justify-between rounded-2xl bg-heading p-3 text-white shadow-elevated">
        <span className="self-end rounded-full bg-white/20 px-1.5 py-0.5 text-[8px]">
          <Sparkles className="mr-0.5 inline h-2 w-2" aria-hidden="true" /> AI INSIGHT
        </span>
        <Play className="h-8 w-8 self-center fill-current" aria-hidden="true" />
        <span className="text-[11px] leading-snug">
          한화오션, 대형
          <br />
          수주로 강세 전환
        </span>
      </div>
    ),
  },
  {
    headline: "AI가 정리한\n투자 판단과 근거",
    description: "매수·중립·매도 판단과 그 이유를 근거와 함께 보여드려요.",
    illustration: (
      <div className="w-full rounded-2xl bg-white p-4 shadow-card">
        <span className="rounded-full bg-market-up/15 px-3 py-1 text-[13px] font-bold text-market-up">
          매수
        </span>
        <div className="mt-3 flex flex-col gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
              <span className="h-2 flex-1 rounded-full bg-surface" style={{ maxWidth: `${90 - i * 12}%` }} />
            </div>
          ))}
        </div>
      </div>
    ),
  },
];

export default function OnboardingCarousel() {
  const [active, setActive] = useState(0);
  const slideRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const observers = slideRefs.current.map((el, i) => {
      if (!el) return null;
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) setActive(i);
        },
        { threshold: 0.6 },
      );
      observer.observe(el);
      return observer;
    });
    return () => observers.forEach((o) => o?.disconnect());
  }, []);

  // 2.5초마다 다음 슬라이드로 자동 스크롤, 마지막에서는 첫 슬라이드로 순환. active가 바뀔 때마다
  // (자동이든 사용자가 직접 스와이프했든) 타이머를 새로 잡아서 매번 "그 슬라이드에 머문 지
  // 2.5초 후" 넘어가게 한다 — 사용자가 스와이프한 직후 곧바로 또 넘어가 버리는 걸 방지.
  useEffect(() => {
    const timer = setTimeout(() => {
      const next = (active + 1) % SLIDES.length;
      slideRefs.current[next]?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    }, 2500);
    return () => clearTimeout(timer);
  }, [active]);

  return (
    <div className="flex flex-1 flex-col">
      <div className="no-scrollbar flex flex-1 snap-x snap-mandatory overflow-x-auto">
        {SLIDES.map((slide, i) => (
          <div
            key={i}
            ref={(el) => {
              slideRefs.current[i] = el;
            }}
            className="flex w-full shrink-0 snap-center flex-col items-center gap-8 px-8 pt-10"
          >
            <div className="flex h-[220px] w-full items-center justify-center rounded-3xl bg-surface p-6">
              {slide.illustration}
            </div>
            <div className="text-center">
              <h1 className="text-[22px] leading-[1.3] font-bold whitespace-pre-line text-heading">
                {slide.headline}
              </h1>
              <p className="mt-3 text-[14px] leading-[1.5] text-caption">{slide.description}</p>
            </div>
          </div>
        ))}
      </div>

      {/* DESIGN_SPEC.md §24.3 Carousel Indicator: inactive는 연한 회색, active는 알약형.
          §24.3의 "mint green"은 레퍼런스 화면(포트폴리오 카드) 기준이고, 779행에서
          "aggregate positive status가 필요한 경우에만 mint 사용"이라 명시 — 온보딩은
          포트폴리오 집계와 무관하므로 이 프로젝트의 실제 active 색(indigo, §0.2 브랜드
          액센트)을 쓴다. */}
      <div className="flex items-center justify-center gap-1.5 py-4">
        {SLIDES.map((_, i) => (
          <span
            key={i}
            className={`h-2 rounded-full transition-all ${
              i === active ? "w-6 bg-primary" : "w-2 bg-border"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
