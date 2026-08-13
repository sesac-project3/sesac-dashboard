"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getAccessToken } from "@/shared/api/base";

// 로그인 여부는 localStorage(클라이언트)에서만 알 수 있어서 서버 렌더링 시점엔 판단이
// 안 된다 — 마운트 전까진 null(판단 중), 이후 true/false로 확정된다.
//
// pathname을 deps에 넣어 라우트가 바뀔 때마다 다시 확인한다 — RootLayout에 박혀서
// 리마운트 안 되는 컴포넌트(BottomTabBar)가 있어서, "마운트 시 1회"만 확인하면
// /login/complete에서 router.replace("/")로 돌아왔을 때(클라이언트 사이드 네비게이션,
// 풀 리로드 아님) 로그인 직후인데도 계속 로그아웃 상태로 고정돼버리는 버그가 있었다.
export function useLoggedIn() {
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    setLoggedIn(!!getAccessToken());
  }, [pathname]);

  return loggedIn;
}
