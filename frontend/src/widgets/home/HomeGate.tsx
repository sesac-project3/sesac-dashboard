"use client";

import { useLoggedIn } from "@/shared/hooks/useLoggedIn";
import OnboardingCarousel from "@/widgets/onboarding/OnboardingCarousel";
import KakaoLoginCta from "@/widgets/onboarding/KakaoLoginCta";
import MarketDashboard from "@/widgets/home/MarketDashboard";

// 프로토타입 단계라 로그인 확인 중(null) 짧은 깜빡임은 감수(제대로 하려면 서버
// 세션/쿠키 기반 인증으로 가야 함).
export default function HomeGate() {
  const loggedIn = useLoggedIn();

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
