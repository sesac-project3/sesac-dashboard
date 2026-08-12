"use client";

import { useEffect, useState } from "react";
import { getAccessToken } from "@/shared/api/base";
import OnboardingCarousel from "@/widgets/onboarding/OnboardingCarousel";
import KakaoLoginCta from "@/widgets/onboarding/KakaoLoginCta";
import MarketDashboard from "@/widgets/home/MarketDashboard";

// 로그인 여부는 localStorage(클라이언트)에서만 알 수 있어서 서버 렌더링 시점엔 판단이
// 안 된다 — 마운트 후 잠깐(한 프레임) 확인 중 상태를 거친다. 프로토타입 단계라
// 이 정도 깜빡임은 감수(제대로 하려면 서버 세션/쿠키 기반 인증으로 가야 함).
export default function HomeGate() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    setLoggedIn(!!getAccessToken());
  }, []);

  if (loggedIn === null) return null;

  if (!loggedIn) {
    return (
      <div className="flex h-full flex-col">
        <OnboardingCarousel />
        <KakaoLoginCta />
      </div>
    );
  }

  return <MarketDashboard />;
}
