"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLoggedIn } from "@/shared/hooks/useLoggedIn";
import { HomeIcon, ProfileIcon, ShortformIcon, WatchlistIcon } from "@/widgets/bottom-tab/icons";

// DESIGN_SPEC.md §27: 레퍼런스 제품(모임투자/포트폴리오 등 Out of Scope 기능)의 탭 이름을
// 그대로 가져오지 않고, 이 제품의 실제 4개 탭(홈/숏폼/관심종목/내 정보)만 노출한다.
// 시각 규칙(치수 72px 고정 / active=indigo, inactive=gray)은 그대로 적용.
const TABS = [
  { href: "/", label: "홈", Icon: HomeIcon },
  { href: "/shortform", label: "숏폼", Icon: ShortformIcon },
  { href: "/watchlist", label: "관심종목", Icon: WatchlistIcon },
  { href: "/profile", label: "내 정보", Icon: ProfileIcon },
] as const;

export default function BottomTabBar() {
  const pathname = usePathname();
  const loggedIn = useLoggedIn();

  // 홈(/)이 로그아웃 상태로 온보딩 캐러셀을 보여줄 땐(HomeGate) 하단 탭도 같이 숨긴다 —
  // 아직 로그인 안 한 사용자에게 다른 탭으로 이동 가능한 것처럼 보이면 안 됨.
  if (pathname === "/" && loggedIn !== true) return null;

  return (
    <nav
      className="flex h-[72px] shrink-0 rounded-t-hero border-t border-border bg-white"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      {TABS.map(({ href, label, Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={`flex flex-1 flex-col items-center justify-center gap-1 transition-transform ${
              active ? "scale-105 text-primary" : "text-caption"
            }`}
          >
            <Icon className="h-6 w-6" />
            <span className={`text-[11px] ${active ? "font-semibold" : ""}`}>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
