"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useLoggedIn } from "@/shared/hooks/useLoggedIn";
import { getWatchlist, type WatchlistStock } from "@/shared/api/watchlists";
import PageContainer from "@/shared/ui/PageContainer";
import Card from "@/shared/ui/Card";

// F-04 관심종목. 홈 화면 랭킹의 하트 토글(POST /watchlists/{code}/toggle)로 등록된 종목을
// 그대로 보여준다 — 로그인 안 했으면 다른 로그인 필요 화면(내 정보)과 같은 패턴으로 홈으로.
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
        <div className="flex flex-col gap-2">
          {stocks.map((stock) => (
            <Link key={stock.code} href={`/stock/${stock.code}`}>
              <Card className="flex items-center justify-between">
                <span className="text-[15px] font-bold text-heading">{stock.name}</span>
                <span className="text-[13px] text-caption">{stock.code}</span>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
