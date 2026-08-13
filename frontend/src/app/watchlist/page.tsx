"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useLoggedIn } from "@/shared/hooks/useLoggedIn";
import { getWatchlist, type WatchlistStock } from "@/shared/api/watchlists";
import PageContainer from "@/shared/ui/PageContainer";
import Card from "@/shared/ui/Card";
import StockLogo from "@/shared/ui/StockLogo";

// F-04 관심종목. 홈 화면 랭킹의 하트 토글(POST /watchlists/{code}/toggle)로 등록된 종목을
// 가격/등락(홈 랭킹과 동일한 KIS 실데이터, 동일 표기)과 함께 보여준다 — 로그인 안 했으면
// 다른 로그인 필요 화면(내 정보)과 같은 패턴으로 홈으로 보낸다.
export default function WatchlistPage() {
  const router = useRouter();
  const loggedIn = useLoggedIn();
  const [stocks, setStocks] = useState<WatchlistStock[] | null>(null);

  useEffect(() => {
    if (loggedIn === false) {
      router.replace("/login");
      return;
    }
    if (loggedIn === true) {
      getWatchlist()
        .then(setStocks)
        .catch(() => setStocks([]));
    }
  }, [loggedIn, router]);

  if (!loggedIn) return null;

  return (
    <PageContainer>
      <h1 className="my-4 text-[18px] font-semibold text-heading">관심종목</h1>
      {stocks === null ? (
        <Card className="h-[60px] animate-pulse bg-surface">{null}</Card>
      ) : stocks.length === 0 ? (
        <Card className="text-center text-[14px] text-caption">
          아직 담은 종목이 없습니다.
        </Card>
      ) : (
        <Card className="flex flex-col divide-y divide-border-soft/60">
          {stocks.map((stock) => (
            <Link
              key={stock.code}
              href={`/stock/${stock.code}`}
              className="flex items-center justify-between py-3.5 first:pt-0 last:pb-0 transition-colors hover:bg-gray-50/50 dark:hover:bg-gray-800/20"
            >
              <div className="flex items-center gap-3">
                <StockLogo code={stock.code} name={stock.name} />
                <span className="text-[16px] font-bold text-heading">{stock.name}</span>
              </div>

              <div className="text-right">
                {stock.price === null ? (
                  <p className="text-[13px] text-caption">시세 조회 실패</p>
                ) : (
                  <>
                    <p className="text-[15px] font-bold text-heading">
                      {stock.price.toLocaleString()}원
                    </p>
                    <p
                      className={`text-[12px] font-bold ${
                        stock.isUp ? "text-market-up" : "text-market-down"
                      }`}
                    >
                      {stock.isUp ? "+" : "-"}
                      {Math.abs(stock.change ?? 0).toLocaleString()} (
                      {stock.isUp ? "+" : ""}
                      {(stock.changePercent ?? 0).toFixed(2)}%)
                    </p>
                  </>
                )}
              </div>
            </Link>
          ))}
        </Card>
      )}
    </PageContainer>
  );
}
