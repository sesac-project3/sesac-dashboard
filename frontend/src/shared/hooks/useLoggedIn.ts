"use client";

import { useEffect, useState } from "react";
import { getAccessToken } from "@/shared/api/base";

// 로그인 여부는 localStorage(클라이언트)에서만 알 수 있어서 서버 렌더링 시점엔 판단이
// 안 된다 — 마운트 전까진 null(판단 중), 이후 true/false로 확정된다.
export function useLoggedIn() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    setLoggedIn(!!getAccessToken());
  }, []);

  return loggedIn;
}
