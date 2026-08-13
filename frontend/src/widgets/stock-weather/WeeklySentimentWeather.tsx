import Card from "@/shared/ui/Card";
import { API_BASE_URL } from "@/shared/config/env";
import type { WeeklySentimentResponse } from "@/shared/api/stocks";

async function fetchWeeklySentiments(code: string): Promise<WeeklySentimentResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/stocks/${code}/sentiments/weekly`, { cache: "no-store" });
    if (!res.ok) return null;
    const body = await res.json();
    return body.data;
  } catch {
    return null;
  }
}

export default async function WeeklySentimentWeather({ stockCode }: { stockCode: string }) {
  const data = await fetchWeeklySentiments(stockCode);
  const items = data?.weeklySentiments ?? [];

  if (items.length === 0) {
    return null;
  }

  return (
    <Card className="flex flex-col gap-3">
      <h2 className="flex items-center gap-2 text-[16px] font-semibold text-heading">
        <span>🌤️</span> 주간 뉴스 기상도
      </h2>

      <div className="grid grid-cols-7 gap-1 text-center">
        {items.map((item) => {
          const [, month, dayStr] = item.date.split("-");
          const formattedDate = month && dayStr ? `${month}.${dayStr}` : item.date;

          return (
            <div
              key={item.date}
              className="flex flex-col items-center justify-center rounded-lg bg-slate-50 py-2.5 px-1 transition-all hover:bg-slate-100"
            >
              <span className="text-[11px] font-medium text-caption">{formattedDate}</span>
              <span className="mt-0.5 text-[12px] font-semibold text-heading">{item.day}</span>
              <span className="mt-2 text-[22px] leading-none" title={item.sentiment}>
                {item.emoji}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
