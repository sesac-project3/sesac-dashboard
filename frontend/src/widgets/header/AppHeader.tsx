"use client";

import { usePathname, useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";

// DESIGN_SPEC.md §9 Global App Shell / Header — 56px, bottom border, center title.
const PAGE_TITLES: Record<string, string> = {
  "/": "홈",
  "/shortform": "숏폼",
  "/login": "내 정보",
};

export default function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const isStockDetail = pathname.startsWith("/stock/");
  const title = "📈 🌤️ 📱"
  return (
    <header
      className="sticky top-0 z-10 flex h-14 shrink-0 items-center justify-center border-b border-border bg-white/90 backdrop-blur"
      style={{ paddingTop: "env(safe-area-inset-top)" }}
    >
      {isStockDetail && (
        <button
          type="button"
          aria-label="뒤로가기"
          className="absolute left-4 cursor-pointer text-caption"
          onClick={() => router.back()}
        >
          <ChevronLeft aria-hidden="true" size={24} strokeWidth={2} />
        </button>
      )}
      <span className="text-[18px] font-semibold text-heading">{title}</span>
    </header>
  );
}
