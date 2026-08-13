import base, { type ApiEnvelope } from "@/shared/api/base";

export interface WatchlistStock {
  code: string;
  name: string;
  market: string;
  price: number | null;
  change: number | null;
  changePercent: number | null;
  isUp: boolean | null;
}

export const getWatchlist = () =>
  base.get<ApiEnvelope<WatchlistStock[]>>("/watchlists").then((res) => res.data.data ?? []);

export const toggleWatchlist = (code: string) =>
  base
    .post<ApiEnvelope<{ inWatchlist: boolean }>>(`/watchlists/${code}/toggle`)
    .then((res) => res.data.data!);
