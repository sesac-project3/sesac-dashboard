"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setTokens } from "@/shared/api/base";

// 백엔드 /auth/kakao/callback이 JWT 발급 후 이 페이지로 302 리다이렉트한다
// (?access_token=...&refresh_token=...). 여기서 받아 저장만 하고 홈으로 보낸다.
function LoginCompleteInner() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    if (accessToken && refreshToken) {
      setTokens(accessToken, refreshToken);
      router.replace("/");
    } else {
      router.replace("/login");
    }
  }, [params, router]);

  return <p className="p-8 text-sm text-neutral-500">로그인 처리 중...</p>;
}

export default function LoginCompletePage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-neutral-500">로그인 처리 중...</p>}>
      <LoginCompleteInner />
    </Suspense>
  );
}
