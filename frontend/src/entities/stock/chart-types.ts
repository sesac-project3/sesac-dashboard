export type CandleInterval = "DAILY" | "WEEKLY" | "MONTHLY" | "MINUTE_15";

export interface Candle {
  timestamp: string;
  openPrice: number;
  highPrice: number;
  lowPrice: number;
  closePrice: number;
  volume: number;
}

export interface CandleResponse {
  stockCode: string;
  stockName: string;
  interval: CandleInterval;
  source: "DB" | "DB_REDIS";
  candles: Candle[];
}

export interface CandleSnapshotMessage {
  type: "candle_snapshot";
  stockCode: string;
  interval: CandleInterval;
  candle: Candle;
  updatedAt: string;
}

export interface CandleUpdateMessage {
  type: "candle_update";
  stockCode: string;
  interval: CandleInterval;
  candle: Candle;
  updatedAt: string;
}

export type CandleWebSocketMessage = CandleSnapshotMessage | CandleUpdateMessage;
