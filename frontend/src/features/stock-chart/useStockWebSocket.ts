"use client";

import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/shared/config/env";
import type {
  Candle,
  CandleInterval,
  CandleWebSocketMessage,
  Quote,
} from "@/entities/stock/chart-types";

const RECONNECT_DELAY_MS = 2_000;

type ConnectionState = "idle" | "connecting" | "open" | "closed";

const buildWebSocketUrl = () => {
  const url = new URL(API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `${url.pathname.replace(/\/$/, "")}/stocks/ws`;
  return url.toString();
};

export default function useStockWebSocket(stockCode: string) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const shouldReconnectRef = useRef(true);
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [candlesByInterval, setCandlesByInterval] = useState<Partial<Record<CandleInterval, Candle>>>({});
  const [quote, setQuote] = useState<Quote | null>(null);

  useEffect(() => {
    if (!stockCode) return;

    shouldReconnectRef.current = true;

    const connect = () => {
      console.log("[stock-ws] connect", { stockCode });
      if (!shouldReconnectRef.current) {
        setConnectionState("closed");
        return;
      }

      setConnectionState("connecting");
      const socket = new WebSocket(buildWebSocketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        console.log("[stock-ws] open", { stockCode });
        setConnectionState("open");
        socket.send(JSON.stringify({ type: "subscribe", stockCode }));
      };

      socket.onmessage = ({ data }: MessageEvent<string>) => {
        let message: CandleWebSocketMessage;
        try {
          message = JSON.parse(data) as CandleWebSocketMessage;
        } catch {
          return;
        }

        if (message.type === "quote_update" || message.type === "quote_snapshot") {
          setQuote(message);
          return;
        }

        if (message.type !== "candle_snapshot" && message.type !== "candle_update") return;
        setCandlesByInterval((previous) => ({ ...previous, [message.interval]: message.candle }));
      };

      socket.onclose = () => {
        console.warn("[stock-ws] close", { stockCode });
        if (socketRef.current === socket) socketRef.current = null;
        setConnectionState("closed");
        if (shouldReconnectRef.current) {
          reconnectTimerRef.current = window.setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      socket.onerror = () => socket.close();
    };

    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current !== null) window.clearTimeout(reconnectTimerRef.current);
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: "unsubscribe", stockCode }));
      }
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [stockCode]);

  return { connectionState, candlesByInterval, quote };
}
