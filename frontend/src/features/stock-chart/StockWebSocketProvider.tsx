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
import { AUTH_TOKEN_CHANGED_EVENT, getAccessToken, refreshAccessToken } from "@/shared/api/base";
import type { CandleWebSocketMessage, IndexMessage } from "@/entities/stock/chart-types";

const RECONNECT_DELAY_MS = 2_000;
const AUTH_TIMEOUT_MS = 5_000;

export type StockWebSocketConnectionState = "idle" | "connecting" | "open" | "closed";
type MessageListener = (message: CandleWebSocketMessage) => void;
type IndexMessageListener = (message: IndexMessage) => void;
type OutgoingMessage = { type: string; stockCode?: string; indexCode?: string; accessToken?: string };

interface StockWebSocketContextValue {
  connectionState: StockWebSocketConnectionState;
  subscribe: (stockCode: string, listener: MessageListener) => () => void;
  subscribeIndex: (indexCode: string, listener: IndexMessageListener) => () => void;
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
  const connectTimerRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const authTimerRef = useRef<number | null>(null);
  const heartbeatTimerRef = useRef<number | null>(null);
  const pongTimerRef = useRef<number | null>(null);
  const tokenRef = useRef<string | null | undefined>(undefined);
  const authenticatedRef = useRef(false);
  const subscriptionsRef = useRef(new Map<string, Set<MessageListener>>());
  const indexSubscriptionsRef = useRef(new Map<string, Set<IndexMessageListener>>());
  const intentionalCloseRef = useRef(false);
  const connectRef = useRef<() => void>(() => undefined);
  const [connectionState, setConnectionState] = useState<StockWebSocketConnectionState>("idle");

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current !== null) window.clearTimeout(reconnectTimerRef.current);
    if (connectTimerRef.current !== null) window.clearTimeout(connectTimerRef.current);
    if (authTimerRef.current !== null) window.clearTimeout(authTimerRef.current);
    if (heartbeatTimerRef.current !== null) window.clearInterval(heartbeatTimerRef.current);
    if (pongTimerRef.current !== null) window.clearTimeout(pongTimerRef.current);
    reconnectTimerRef.current = null;
    connectTimerRef.current = null;
    authTimerRef.current = null;
    heartbeatTimerRef.current = null;
    pongTimerRef.current = null;
  }, []);

  const send = useCallback((message: OutgoingMessage) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
  }, []);

  const subscribe = useCallback((stockCode: string, listener: MessageListener) => {
    const listeners = subscriptionsRef.current.get(stockCode) ?? new Set<MessageListener>();
    const wasEmpty = listeners.size === 0;
    listeners.add(listener);
    subscriptionsRef.current.set(stockCode, listeners);
    if (wasEmpty && authenticatedRef.current) {
      console.log("[stock-ws] subscribe", { stockCode });
      send({ type: "subscribe", stockCode });
    }

    return () => {
      const current = subscriptionsRef.current.get(stockCode);
      if (!current) return;
      current.delete(listener);
      if (current.size > 0) return;
      subscriptionsRef.current.delete(stockCode);
      if (authenticatedRef.current) {
        console.log("[stock-ws] unsubscribe", { stockCode });
        send({ type: "unsubscribe", stockCode });
      }
    };
  }, [send]);

  const subscribeIndex = useCallback((indexCode: string, listener: IndexMessageListener) => {
    const listeners = indexSubscriptionsRef.current.get(indexCode) ?? new Set<IndexMessageListener>();
    const wasEmpty = listeners.size === 0;
    listeners.add(listener);
    indexSubscriptionsRef.current.set(indexCode, listeners);
    if (wasEmpty && authenticatedRef.current) {
      console.log("[stock-ws] subscribe index", { indexCode });
      send({ type: "subscribe_index", indexCode });
    }

    return () => {
      const current = indexSubscriptionsRef.current.get(indexCode);
      if (!current) return;
      current.delete(listener);
      if (current.size > 0) return;
      indexSubscriptionsRef.current.delete(indexCode);
      if (authenticatedRef.current) {
        console.log("[stock-ws] unsubscribe index", { indexCode });
        send({ type: "unsubscribe_index", indexCode });
      }
    };
  }, [send]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    authenticatedRef.current = false;
    clearTimers();
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.CONNECTING) {
      socket.onopen = () => socket.close();
    } else {
      socket?.close();
    }
    socketRef.current = null;
    setConnectionState("idle");
  }, [clearTimers]);

  const scheduleConnect = useCallback(() => {
    if (
      connectTimerRef.current !== null ||
      reconnectTimerRef.current !== null ||
      socketRef.current
    ) return;
    connectTimerRef.current = window.setTimeout(() => {
      connectTimerRef.current = null;
      connectRef.current();
    }, 0);
  }, []);

  const connect = useCallback(() => {
    const token = tokenRef.current;
    if (!token || socketRef.current) return;

    intentionalCloseRef.current = false;
    setConnectionState("connecting");
    const socket = new WebSocket(buildWebSocketUrl());
    socketRef.current = socket;
    console.log("[stock-ws] connect");

    socket.onopen = () => {
      console.log("[stock-ws] open");
      authenticatedRef.current = false;
      send({ type: "auth", accessToken: token });
      authTimerRef.current = window.setTimeout(() => socket.close(), AUTH_TIMEOUT_MS);
    };

    socket.onmessage = ({ data }: MessageEvent<string>) => {
      if (socketRef.current !== socket) return;
      let message: CandleWebSocketMessage | IndexMessage | { type: "authenticated" | "pong" };
      try {
        message = JSON.parse(data) as CandleWebSocketMessage | IndexMessage | { type: "authenticated" | "pong" };
      } catch {
        return;
      }

      if (message.type === "authenticated") {
        console.log("[stock-ws] authenticated");
        if (authTimerRef.current !== null) window.clearTimeout(authTimerRef.current);
        authTimerRef.current = null;
        authenticatedRef.current = true;
        setConnectionState("open");
        for (const stockCode of subscriptionsRef.current.keys()) {
          console.log("[stock-ws] subscribe restored", { stockCode });
          send({ type: "subscribe", stockCode });
        }
        for (const indexCode of indexSubscriptionsRef.current.keys()) {
          console.log("[stock-ws] subscribe index restored", { indexCode });
          send({ type: "subscribe_index", indexCode });
        }
        heartbeatTimerRef.current = window.setInterval(() => {
          if (socketRef.current !== socket || socket.readyState !== WebSocket.OPEN) return;
          send({ type: "ping" });
          if (pongTimerRef.current !== null) window.clearTimeout(pongTimerRef.current);
          pongTimerRef.current = window.setTimeout(() => {
            console.warn("[stock-ws] pong timeout; closing socket");
            socket.close();
          }, 10_000);
        }, 30_000);
        return;
      }

      if (message.type === "pong") {
        if (pongTimerRef.current !== null) window.clearTimeout(pongTimerRef.current);
        pongTimerRef.current = null;
        return;
      }

      if (message.type === "index_snapshot" || message.type === "index_update") {
        for (const listener of indexSubscriptionsRef.current.get(message.indexCode)?.values() ?? []) {
          listener(message);
        }
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
      if (intentionalCloseRef.current || !tokenRef.current) return;

      // 서버가 인증 실패(1008: 토큰 만료/무효)로 닫은 경우 같은 토큰으로 그냥 재연결하면
      // 똑같이 거부되는 무한 루프가 된다 — REST 401 인터셉터와 같은 절차로 먼저 갱신한다.
      // 갱신 성공 시 setTokens가 AUTH_TOKEN_CHANGED_EVENT를 쏴서 아래 syncToken이 새
      // 토큰으로 재연결하므로 여기서 직접 재연결하지 않는다.
      if (code === 1008) {
        refreshAccessToken().catch(() => {
          console.warn("[stock-ws] token refresh failed after auth rejection; giving up");
        });
        return;
      }

      if (reconnectTimerRef.current === null) {
        console.log("[stock-ws] reconnect scheduled", { delayMs: RECONNECT_DELAY_MS });
        reconnectTimerRef.current = window.setTimeout(() => {
          reconnectTimerRef.current = null;
          connectRef.current();
        }, RECONNECT_DELAY_MS);
      }
    };

    socket.onerror = () => {
      if (socket.readyState === WebSocket.CONNECTING) {
        socket.onopen = () => socket.close();
        return;
      }
      socket.close();
    };
  }, [clearTimers, send]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    const syncToken = () => {
      const nextToken = getAccessToken();
      if (nextToken === tokenRef.current) {
        if (nextToken && !socketRef.current) scheduleConnect();
        return;
      }
      tokenRef.current = nextToken;
      disconnect();
      if (nextToken) scheduleConnect();
    };

    syncToken();
    window.addEventListener(AUTH_TOKEN_CHANGED_EVENT, syncToken);
    window.addEventListener("storage", syncToken);
    return () => {
      window.removeEventListener(AUTH_TOKEN_CHANGED_EVENT, syncToken);
      window.removeEventListener("storage", syncToken);
      disconnect();
    };
  }, [connect, disconnect, scheduleConnect]);

  const value = useMemo(
    () => ({ connectionState, subscribe, subscribeIndex }),
    [connectionState, subscribe, subscribeIndex],
  );

  return <StockWebSocketContext.Provider value={value}>{children}</StockWebSocketContext.Provider>;
}

export function useStockWebSocketContext() {
  const context = useContext(StockWebSocketContext);
  if (!context) throw new Error("useStockWebSocketContext must be used within StockWebSocketProvider");
  return context;
}
