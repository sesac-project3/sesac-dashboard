"use client";

import type { CandleInterval } from "@/entities/stock/chart-types";

export const CHART_TABS = [
  { label: "15분", interval: "MINUTE_15" },
  { label: "일", interval: "DAILY" },
  { label: "주", interval: "WEEKLY" },
  { label: "월", interval: "MONTHLY" },
] as const satisfies ReadonlyArray<{ label: string; interval: CandleInterval | null }>;

export default function ChartRangeTabs({
  selected,
  onSelect,
}: {
  selected: number;
  onSelect: (index: number) => void;
}) {
  return (
    <div className="grid grid-cols-4 gap-1 px-1">
      {CHART_TABS.map((tab, index) => (
        <button
          key={tab.label}
          type="button"
          aria-pressed={selected === index}
          onClick={() => onSelect(index)}
          className={`h-10 cursor-pointer rounded-xl text-[18px] font-semibold transition-colors ${
            selected === index ? "bg-surface text-heading" : "text-heading"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
