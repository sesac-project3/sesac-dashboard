"use client";

import { useEffect, useState } from "react";
import type { IndexMessage } from "@/entities/stock/chart-types";
import { useStockWebSocketContext } from "./StockWebSocketProvider";

const INDEX_CODES = ["0001", "1001"] as const;

export default function useMarketIndexSubscription() {
  const { connectionState, subscribeIndex } = useStockWebSocketContext();
  const [updates, setUpdates] = useState<Partial<Record<"KOSPI" | "KOSDAQ", IndexMessage>>>({});

  useEffect(() => {
    const cleanups = INDEX_CODES.map((indexCode) =>
      subscribeIndex(indexCode, (message) => {
        setUpdates((previous) => ({ ...previous, [message.indexType]: message }));
      }),
    );
    return () => cleanups.forEach((cleanup) => cleanup());
  }, [subscribeIndex]);

  return { connectionState, updates };
}
