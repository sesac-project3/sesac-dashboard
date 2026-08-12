"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// DESIGN_SPEC.md §27: 기존 navigation 구조를 유지한다 — 이 제품의 실제 탭은
// PRD 범위(홈/숏폼/내 정보)를 따르고, 레퍼런스 제품(모임투자/포트폴리오 등 Out of
// Scope 기능)의 탭 이름을 그대로 가져오지 않는다. 시각 규칙(치수/색)만 적용.
const TABS = [
  { href: "/", label: "홈" },
  { href: "/shortform", label: "숏폼" },
  { href: "/login", label: "내 정보" },
] as const;

export default function BottomTabBar() {
  const pathname = usePathname();

  return (
    <nav
      className="flex h-[72px] shrink-0 rounded-t-hero border-t border-border bg-white"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`flex flex-1 items-center justify-center text-[13px] transition-transform ${
              active ? "scale-105 font-semibold text-primary" : "text-caption"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
