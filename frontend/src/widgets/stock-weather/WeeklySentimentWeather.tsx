"use client";

import { useEffect, useRef, useState } from "react";
import Card from "@/shared/ui/Card";
import { API_BASE_URL } from "@/shared/config/env";
import type { DailySentimentItem, WeeklySentimentResponse } from "@/shared/api/stocks";

export default function WeeklySentimentWeather({ stockCode }: { stockCode: string }) {
  const [items, setItems] = useState<DailySentimentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Drag state
  const isDragging = useRef(false);
  const startX = useRef(0);
  const scrollLeftStart = useRef(0);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const res = await fetch(`${API_BASE_URL}/stocks/${stockCode}/sentiments/weekly`, {
          cache: "no-store",
        });
        if (!res.ok) return;
        const body = await res.json();
        const list: DailySentimentItem[] = body.data?.weeklySentiments ?? [];
        if (isMounted) {
          setItems(list);
        }
      } catch (err) {
        console.error("Failed to load sentiment weather", err);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [stockCode]);

  // Auto-scroll to the end (most recent yesterday dates) when data is loaded
  useEffect(() => {
    if (items.length > 0 && scrollRef.current) {
      scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
    }
  }, [items]);

  // Navigation button handlers (scroll by 7 items width ~ 300px)
  const handleScrollLeft = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({ left: -300, behavior: "smooth" });
    }
  };

  const handleScrollRight = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({ left: 300, behavior: "smooth" });
    }
  };

  // Mouse Drag Events
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!scrollRef.current) return;
    isDragging.current = true;
    startX.current = e.pageX - scrollRef.current.offsetLeft;
    scrollLeftStart.current = scrollRef.current.scrollLeft;
  };

  const handleMouseLeaveOrUp = () => {
    isDragging.current = false;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current || !scrollRef.current) return;
    e.preventDefault();
    const x = e.pageX - scrollRef.current.offsetLeft;
    const walk = (x - startX.current) * 1.5;
    scrollRef.current.scrollLeft = scrollLeftStart.current - walk;
  };

  if (isLoading || items.length === 0) {
    return null;
  }

  return (
    <Card className="flex flex-col gap-3 selection:bg-none">
      {/* Header */}
      <h2 className="flex items-center gap-2 text-[16px] font-semibold text-heading">
        <span>🌤️</span> 주간 뉴스 기상도
      </h2>

      {/* Relative Container for Side Arrow Placement */}
      <div className="relative flex items-center px-1">
        {/* Left Arrow Button (Side Placement) */}
        <button
          type="button"
          onClick={handleScrollLeft}
          className="absolute -left-2 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white text-[18px] font-semibold text-slate-700 shadow-md border border-slate-200 transition-all hover:bg-slate-50 hover:scale-105 active:scale-95"
          title="과거 7일 이동"
        >
          ‹
        </button>

        {/* Horizontal Draggable & Scrollable Container */}
        <div
          ref={scrollRef}
          onMouseDown={handleMouseDown}
          onMouseLeave={handleMouseLeaveOrUp}
          onMouseUp={handleMouseLeaveOrUp}
          onMouseMove={handleMouseMove}
          className="flex items-center gap-2 overflow-x-auto scroll-smooth py-1 px-3 cursor-grab active:cursor-grabbing no-scrollbar"
          style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
        >
          {items.map((item) => {
            const [, month, dayStr] = item.date.split("-");
            const formattedDate = month && dayStr ? `${month}.${dayStr}` : item.date;

            return (
              <div
                key={item.date}
                className="flex w-[62px] shrink-0 flex-col items-center justify-center rounded-xl bg-slate-50 py-3 px-1 transition-all hover:bg-slate-100 hover:shadow-sm"
              >
                <span className="text-[11px] font-medium text-caption">{formattedDate}</span>
                <span className="mt-0.5 text-[12px] font-semibold text-heading">{item.day}</span>
                <span className="mt-2 text-[22px] leading-none select-none" title={item.sentiment}>
                  {item.emoji}
                </span>
              </div>
            );
          })}
        </div>

        {/* Right Arrow Button (Side Placement) */}
        <button
          type="button"
          onClick={handleScrollRight}
          className="absolute -right-2 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white text-[18px] font-semibold text-slate-700 shadow-md border border-slate-200 transition-all hover:bg-slate-50 hover:scale-105 active:scale-95"
          title="최근 7일 이동"
        >
          ›
        </button>
      </div>
    </Card>
  );
}
