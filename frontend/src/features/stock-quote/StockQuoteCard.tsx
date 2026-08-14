"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Heart, Triangle } from "lucide-react";
import { getAccessToken } from "@/shared/api/base";
import { getWatchlist, toggleWatchlist } from "@/shared/api/watchlists";
import Button from "@/shared/ui/Button";

import type { Quote } from "@/entities/stock/chart-types";

export default function StockQuoteCard({
  stockCode,
  stockName,
  market,
  exchange,
  quote,
}: {
  stockCode: string;
  stockName: string;
  market: string;
  exchange: string;
  quote: Quote | null;
}) {
  const router = useRouter();
  const [isFav, setIsFav] = useState(false);
  const requestChain = useRef<Promise<unknown>>(Promise.resolve());
  const latestRequestId = useRef(0);

  const isDown = quote?.changeDirection === "DOWN";
  const color = !quote ? "text-caption" : isDown ? "text-market-down" : "text-market-up";

  // Load watchlist on mount to see if this stock is already favorited
  useEffect(() => {
    if (!getAccessToken()) return;
    getWatchlist()
      .then((list) => {
        const found = list.some((item) => item.code === stockCode);
        setIsFav(found);
      })
      .catch(() => {
        // Silently ignore retrieval failure
      });
  }, [stockCode]);

  // Optimistic UI updates with request chain to prevent DB locks/races on multiple fast clicks
  const handleToggleFavorite = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!getAccessToken()) {
      router.push("/login");
      return;
    }

    const previous = isFav;
    setIsFav(!previous);

    const requestId = latestRequestId.current + 1;
    latestRequestId.current = requestId;

    requestChain.current = requestChain.current
      .then(
        () => toggleWatchlist(stockCode),
        () => toggleWatchlist(stockCode) // Continue next request even if previous failed
      )
      .then(
        (result) => {
          if (latestRequestId.current !== requestId) return;
          setIsFav(result.inWatchlist);
        },
        () => {
          if (latestRequestId.current !== requestId) return;
          setIsFav(previous);
        }
      );
  };

  return (
    <div className="flex flex-col gap-[14px] px-5 pt-6 pb-4">
      <div className="relative flex flex-col gap-1">
        <Button
          variant="icon"
          onClick={handleToggleFavorite}
          aria-label={isFav ? "관심종목 해제" : "관심종목 등록"}
          className="absolute top-0 right-0 cursor-pointer text-heading transition-transform active:scale-90"
        >
          <Heart
            aria-hidden="true"
            size={24}
            strokeWidth={1.8}
            fill={isFav ? "currentColor" : "none"}
            className={isFav ? "text-market-up" : "text-neutral-300"}
          />
        </Button>
        <h1 className="text-[28px] leading-none font-bold tracking-[-0.04em] text-heading">
          {stockName}
        </h1>
        <p className="text-[14px] leading-none text-caption">
          {stockCode} <span aria-hidden="true">|</span> {market} <span aria-hidden="true">|</span>{" "}
          {exchange}
        </p>
      </div>
      {quote ? (
        <div className="flex flex-col gap-2">
          <p className={`text-[40px] leading-none font-bold tracking-[-0.04em] ${color}`}>
            {quote.currentPrice.toLocaleString()}
          </p>
          <div className={`flex min-h-6 items-center gap-3 text-[18px] leading-none font-medium ${color}`}>
              <span className="flex items-center gap-1">
                <Triangle
                  aria-hidden="true"
                  className={isDown ? "rotate-180" : ""}
                  fill="currentColor"
                  height={16}
                  width={16}
                  strokeWidth={0}
                />
                {Math.abs(quote.changePrice).toLocaleString()}
              </span>
              <span className="h-4 w-px bg-border" aria-hidden="true" />
              <span>{quote.changeRate >= 0 ? "+" : "-"}{Math.abs(quote.changeRate).toFixed(2)}%</span>
          </div>
        </div>
      ) : (
        <div className="flex animate-pulse flex-col gap-2" aria-label="시세를 불러오는 중" aria-busy="true">
          <span className="h-10 w-56 rounded-md bg-surface" />
          <span className="h-6 w-40 rounded-md bg-surface" />
        </div>
      )}
    </div>
  );
}
