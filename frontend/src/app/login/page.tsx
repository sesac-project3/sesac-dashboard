"use client";

import { redirectToKakaoLogin } from "@/shared/api/auth";
import PageContainer from "@/shared/ui/PageContainer";

export default function LoginPage() {
  return (
    <PageContainer>
      <div className="flex flex-col items-center gap-6 py-16 text-center">
        <h1 className="text-[22px] font-semibold text-heading">로그인</h1>
        <p className="text-[14px] text-caption">
          카카오 계정으로 로그인하고
          <br />
          관심 종목을 관리해보세요.
        </p>
        <button
          onClick={redirectToKakaoLogin}
          className="h-[52px] w-full rounded-sm bg-[#FEE500] text-[15px] font-medium text-black/85 transition active:scale-[0.98]"
        >
          카카오로 로그인
        </button>
      </div>
    </PageContainer>
  );
}
