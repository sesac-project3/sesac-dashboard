"use client";

import { useState } from "react";

// 종목코드 기준 fallback(색/이니셜) — public/img/stocks/{코드}.png가 없거나 로드 실패할 때만 씀.
const LOGO_FALLBACK: Record<string, { bg: string; text: string }> = {
  "005930": { bg: "bg-blue-600", text: "SEC" },
  "000660": { bg: "bg-red-500", text: "SK" },
  "005380": { bg: "bg-blue-700", text: "HD" },
  "373220": { bg: "bg-emerald-600", text: "LGE" },
  "042660": { bg: "bg-orange-500", text: "한화" },
};

export default function StockLogo({ code, name }: { code: string; name: string }) {
  const [failed, setFailed] = useState(false);

  if (!failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- public/ 정적 아이콘 5개뿐, next/image 불필요
      <img
        src={`/img/stocks/${code}.png`}
        alt={name}
        className="h-9 w-9 shrink-0 rounded-full object-cover shadow-sm"
        onError={() => setFailed(true)}
      />
    );
  }

  const fallback = LOGO_FALLBACK[code] ?? { bg: "bg-gray-400", text: name.slice(0, 2) };
  return (
    <div
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white shadow-sm ${fallback.bg}`}
    >
      {fallback.text}
    </div>
  );
}
