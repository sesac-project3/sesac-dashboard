"use client";

import { usePathname } from "next/navigation";

// DESIGN_SPEC.md §9 Global App Shell / Header — 56px, bottom border, center title.
const PAGE_TITLES: Record<string, string> = {
  "/": "홈",
  "/shortform": "숏폼",
  "/login": "내 정보",
};

export default function AppHeader() {
  const pathname = usePathname();
  const title = PAGE_TITLES[pathname] ?? "🌱 세싹대시보드";

  return (
    <header
      className="sticky top-0 z-10 flex h-14 shrink-0 items-center justify-center border-b border-border bg-white/90 backdrop-blur"
      style={{ paddingTop: "env(safe-area-inset-top)" }}
    >
      <span className="text-[18px] font-semibold text-heading">{title}</span>
    </header>
  );
}
