"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "홈" },
  { href: "/shortform", label: "숏폼" },
  { href: "/login", label: "내 정보" },
] as const;

export default function BottomTab() {
  const pathname = usePathname();

  return (
    <nav className="sticky bottom-0 flex border-t border-black/10 bg-[var(--background)]">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`flex-1 py-3 text-center text-sm ${
              active ? "font-semibold text-blue-600" : "text-black/60"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
