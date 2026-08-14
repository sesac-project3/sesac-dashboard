"use client";

import { redirectToKakaoLogin } from "@/shared/api/auth";
import Button from "@/shared/ui/Button";

export default function KakaoLoginCta() {
  return (
    <div className="shrink-0 px-6 pb-6">
      <Button
        onClick={redirectToKakaoLogin}
        className="h-[52px] w-full !bg-kakao !text-black/85"
      >
        3초만에 카카오로 시작하기
      </Button>
      <p className="mt-3 text-center text-[12px] text-caption">
        시작하면 이용약관 및 개인정보처리방침에 동의하게 됩니다.
      </p>
    </div>
  );
}
