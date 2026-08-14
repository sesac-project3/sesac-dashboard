"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, CloudRain, CloudSun, Sun } from "lucide-react";
import Card from "@/shared/ui/Card";
import Button from "@/shared/ui/Button";
import { getWeeklyStockSentiments, type DailySentimentItem } from "@/shared/api/stocks";

const WINDOW = 7; // items visible at once
const STEP = 7;  // items to jump per button click

export default function WeeklySentimentWeather({ stockCode }: { stockCode: string }) {
  const [items, setItems] = useState<DailySentimentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  // startIndex: index of the leftmost visible item
  const [startIndex, setStartIndex] = useState(0);

  // Drag state
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const [dragOffset, setDragOffset] = useState(0);

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const data = await getWeeklyStockSentiments(stockCode);
        const list: DailySentimentItem[] = data?.weeklySentiments ?? [];
        if (isMounted) {
          setItems(list);
          setHasError(false);
          // Start so that yesterday (last item) is at the rightmost position
          setStartIndex(Math.max(0, list.length - WINDOW));
        }
      } catch (err) {
        console.error("Failed to load sentiment weather", err);
        if (isMounted) setHasError(true);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    loadData();
    return () => { isMounted = false; };
  }, [stockCode]);

  if (isLoading) {
    return <div className="h-[180px] animate-pulse rounded-lg bg-surface" aria-label="주간 뉴스 기상도 로딩 중" />;
  }

  if (hasError) {
    return (
      <Card className="flex min-h-[180px] items-center justify-center text-center text-[12px] text-caption">
        주간 뉴스 기상도를 불러오지 못했어요.
      </Card>
    );
  }

  if (items.length === 0) return null;

  const canGoPrev = startIndex > 0;
  const canGoNext = startIndex < items.length - WINDOW;

  const goLeft = () =>
    setStartIndex((i) => Math.max(0, i - STEP));

  const goRight = () =>
    setStartIndex((i) => Math.min(items.length - WINDOW, i + STEP));

  // Drag handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    dragStartX.current = e.clientX;
    setDragOffset(0);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current) return;
    e.preventDefault();
    setDragOffset(e.clientX - dragStartX.current);
  };

  const handleMouseUp = () => {
    if (!isDragging.current) return;
    isDragging.current = false;
    const containerWidth = containerRef.current?.offsetWidth ?? 400;
    const itemWidth = containerWidth / WINDOW;
    const threshold = itemWidth * 1.5;

    if (dragOffset < -threshold && canGoNext) {
      goRight();
    } else if (dragOffset > threshold && canGoPrev) {
      goLeft();
    }
    setDragOffset(0);
  };

  // Calculate transform: each item is (100/WINDOW)% of container
  const containerWidth = containerRef.current?.offsetWidth ?? 400;
  const itemWidthPct = 100 / WINDOW;
  const dragOffsetPct = (dragOffset / containerWidth) * 100;
  const translateX = -(startIndex * itemWidthPct) + dragOffsetPct;

  return (
    <Card className="flex flex-col gap-2 selection:bg-none">
      {/* Title & Navigation Header */}
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-[16px] font-semibold text-heading">
          <CloudSun aria-hidden="true" className="h-[18px] w-[18px] text-neutral-500" /> 주간 뉴스 기상도
        </h2>

        <div className="flex items-center gap-1">
          <Button
            variant="icon"
            onClick={goLeft}
            disabled={!canGoPrev}
            className={`flex h-7 w-7 items-center justify-center rounded-full font-bold transition-all ${
              canGoPrev
                ? "bg-neutral-100 text-neutral-700 hover:bg-neutral-200 active:scale-95 cursor-pointer"
                : "bg-neutral-100/50 text-neutral-300 cursor-not-allowed opacity-40"
            }`}
            title={canGoPrev ? "이전 7일" : "처음 데이터입니다"}
          >
            <ChevronLeft aria-hidden="true" className="h-4 w-4" />
          </Button>
          <Button
            variant="icon"
            onClick={goRight}
            disabled={!canGoNext}
            className={`flex h-7 w-7 items-center justify-center rounded-full font-bold transition-all ${
              canGoNext
                ? "bg-neutral-100 text-neutral-700 hover:bg-neutral-200 active:scale-95 cursor-pointer"
                : "bg-neutral-100/50 text-neutral-300 cursor-not-allowed opacity-40"
            }`}
            title={canGoNext ? "다음 7일" : "최신 데이터입니다"}
          >
            <ChevronRight aria-hidden="true" className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Viewport: overflow hidden, always shows exactly 7 items */}
      <div
        ref={containerRef}
        className="overflow-hidden py-1"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Full strip of ALL items, moved via translateX */}
        <div
          className="flex"
          style={{
            width: `${(items.length / WINDOW) * 100}%`,
            transform: `translateX(${translateX / (items.length / WINDOW)}%)`,
            transition: isDragging.current ? "none" : "transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)",
            willChange: "transform",
          }}
        >
          {items.map((item) => {
            const [, month, dayStr] = item.date.split("-");
            const formattedDate = month && dayStr ? `${month}.${dayStr}` : item.date;

            const sentimentBadgeColor =
              item.sentiment === "긍정"
                ? "bg-emerald-600 text-white"
                : item.sentiment === "부정"
                ? "bg-rose-600 text-white"
                : "bg-neutral-800 text-white";

            return (
              <div
                key={item.date}
                className="group flex flex-col items-center justify-center rounded-xl bg-neutral-50 py-2.5 px-1 mx-[3px] transition-colors hover:bg-neutral-100 hover:shadow-sm select-none"
                style={{ width: `calc(${100 / items.length}% - 6px)` }}
              >
                <span className="text-[10px] font-medium text-caption">{formattedDate}</span>
                <span className="mt-0.5 text-[12px] font-semibold text-heading">{item.day}</span>

                <span className="mt-1 leading-none select-none transition-transform duration-200 group-hover:scale-110">
                  {item.sentiment === "긍정" ? (
                    <Sun aria-hidden="true" className="h-5 w-5 text-amber-400" />
                  ) : item.sentiment === "부정" ? (
                    <CloudRain aria-hidden="true" className="h-5 w-5 text-sky-400" />
                  ) : (
                <CloudSun aria-hidden="true" className="h-5 w-5 text-neutral-500" />
                  )}
                </span>

                {/* Hover-only sentiment badge */}
                <div className="mt-1 flex h-[16px] items-center justify-center">
                  <span
                    className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold opacity-0 scale-90 transition-all duration-200 group-hover:opacity-100 group-hover:scale-100 ${sentimentBadgeColor}`}
                  >
                    {item.sentiment}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}
