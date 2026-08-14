"use client";

import { redirectToKakaoLogin } from "@/shared/api/auth";

export default function KakaoLoginCta() {
  return (
    <div className="shrink-0 px-6 pb-6">
      <button
        onClick={redirectToKakaoLogin}
        className="h-[52px] w-full rounded-sm bg-[#FEE500] text-[15px] font-medium text-black/85 transition active:scale-[0.98]"
      >
        3초만에 카카오로 시작하기
      </button>
      <p className="mt-3 text-center text-[12px] text-caption">
        시작하면 이용약관 및 개인정보처리방침에 동의하게 됩니다.
      </p>
    </div>
  );
}
