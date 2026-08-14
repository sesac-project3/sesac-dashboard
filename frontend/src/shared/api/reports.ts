import base, { unwrapApiResponse, type ApiEnvelope } from "@/shared/api/base";
import type { StockReport } from "@/entities/report/types";

export const getStockReport = (code: string) =>
  base.get<ApiEnvelope<StockReport | null>>(`/reports/${code}`).then(unwrapApiResponse);
