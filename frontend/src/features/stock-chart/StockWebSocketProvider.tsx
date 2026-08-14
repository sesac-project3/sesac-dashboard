"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { API_BASE_URL } from "@/shared/config/env";
import { AUTH_TOKEN_CHANGED_EVENT, getAccessToken } from "@/shared/api/base";
import type { CandleWebSocketMessage } from "@/entities/stock/chart-types";

const RECONNECT_DELAY_MS = 2_000;
const AUTH_TIMEOUT_MS = 5_000;

export type StockWebSocketConnectionState = "idle" | "connecting" | "open" | "closed";
type MessageListener = (message: CandleWebSocketMessage) => void;

interface StockWebSocketContextValue {
  connectionState: StockWebSocketConnectionState;
  subscribe: (stockCode: string, listener: MessageListener) => () => void;
}

const StockWebSocketContext = createContext<StockWebSocketContextValue | null>(null);

const buildWebSocketUrl = () => {
  const url = new URL(API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `${url.pathname.replace(/\/$/, "")}/stocks/ws`;
  return url.toString();
};

export default function StockWebSocketProvider({ children }: { children: ReactNode }) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const authTimerRef = useRef<number | null>(null);
  const tokenRef = useRef<string | null | undefined>(undefined);
  const authenticatedRef = useRef(false);
  const subscriptionsRef = useRef(new Map<string, Set<MessageListener>>());
  const intentionalCloseRef = useRef(false);
  const connectRef = useRef<() => void>(() => undefined);
  const [connectionState, setConnectionState] = useState<StockWebSocketConnectionState>("idle");

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current !== null) window.clearTimeout(reconnectTimerRef.current);
    if (authTimerRef.current !== null) window.clearTimeout(authTimerRef.current);
    reconnectTimerRef.current = null;
    authTimerRef.current = null;
  }, []);

  const send = useCallback((message: object) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
  }, []);

  const subscribe = useCallback((stockCode: string, listener: MessageListener) => {
    const listeners = subscriptionsRef.current.get(stockCode) ?? new Set<MessageListener>();
    const wasEmpty = listeners.size === 0;
    listeners.add(listener);
    subscriptionsRef.current.set(stockCode, listeners);
    if (wasEmpty && authenticatedRef.current) send({ type: "subscribe", stockCode });

    return () => {
      const current = subscriptionsRef.current.get(stockCode);
      if (!current) return;
      current.delete(listener);
      if (current.size > 0) return;
      subscriptionsRef.current.delete(stockCode);
      if (authenticatedRef.current) send({ type: "unsubscribe", stockCode });
    };
  }, [send]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    authenticatedRef.current = false;
    clearTimers();
    socketRef.current?.close();
    socketRef.current = null;
    setConnectionState("idle");
  }, [clearTimers]);

  const connect = useCallback(() => {
    const token = tokenRef.current;
    if (!token || socketRef.current) return;

    intentionalCloseRef.current = false;
    setConnectionState("connecting");
    const socket = new WebSocket(buildWebSocketUrl());
    socketRef.current = socket;
    console.log("[stock-ws] connect");

    socket.onopen = () => {
      authenticatedRef.current = false;
      send({ type: "auth", accessToken: token });
      authTimerRef.current = window.setTimeout(() => socket.close(), AUTH_TIMEOUT_MS);
    };

    socket.onmessage = ({ data }: MessageEvent<string>) => {
      let message: CandleWebSocketMessage | { type: "authenticated" };
      try {
        message = JSON.parse(data) as CandleWebSocketMessage | { type: "authenticated" };
      } catch {
        return;
      }

      if (message.type === "authenticated") {
        if (authTimerRef.current !== null) window.clearTimeout(authTimerRef.current);
        authTimerRef.current = null;
        authenticatedRef.current = true;
        setConnectionState("open");
        for (const stockCode of subscriptionsRef.current.keys()) send({ type: "subscribe", stockCode });
        return;
      }

      if (!("stockCode" in message)) return;
      for (const listener of subscriptionsRef.current.get(message.stockCode)?.values() ?? []) {
        listener(message);
      }
    };

    socket.onclose = ({ code, reason }) => {
      if (socketRef.current !== socket) return;
      socketRef.current = null;
      authenticatedRef.current = false;
      clearTimers();
      setConnectionState("closed");
      console.warn("[stock-ws] close", { code, reason: reason || undefined });
      if (!intentionalCloseRef.current && tokenRef.current && reconnectTimerRef.current === null) {
        reconnectTimerRef.current = window.setTimeout(() => {
          reconnectTimerRef.current = null;
          connectRef.current();
        }, RECONNECT_DELAY_MS);
      }
    };

    socket.onerror = () => socket.close();
  }, [clearTimers, send]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    const syncToken = () => {
      const nextToken = getAccessToken();
      if (nextToken === tokenRef.current) return;
      tokenRef.current = nextToken;
      disconnect();
      if (nextToken) connect();
    };

    syncToken();
    window.addEventListener(AUTH_TOKEN_CHANGED_EVENT, syncToken);
    window.addEventListener("storage", syncToken);
    return () => {
      window.removeEventListener(AUTH_TOKEN_CHANGED_EVENT, syncToken);
      window.removeEventListener("storage", syncToken);
      disconnect();
    };
  }, [connect, disconnect]);

  const value = useMemo(() => ({ connectionState, subscribe }), [connectionState, subscribe]);

  return <StockWebSocketContext.Provider value={value}>{children}</StockWebSocketContext.Provider>;
}

export function useStockWebSocketContext() {
  const context = useContext(StockWebSocketContext);
  if (!context) throw new Error("useStockWebSocketContext must be used within StockWebSocketProvider");
  return context;
}
