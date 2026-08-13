"use client";

import { usePathname, useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";

// DESIGN_SPEC.md §9 Global App Shell / Header — 56px, bottom border, center title.
export default function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const isStockDetail = pathname.startsWith("/stock/");
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
      {/* eslint-disable-next-line @next/next/no-img-element -- 헤더 로고 1개뿐, next/image 불필요 */}
      <img
        src="/img/logo/zstock_logo.png"
        alt="Z-STOCK"
        className="h-[42px] w-[225px] object-contain"
      />
    </header>
  );
}
