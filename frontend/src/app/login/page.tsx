"use client";

import { redirectToKakaoLogin } from "@/shared/api/auth";

export default function LoginPage() {
  return (
    <div className="flex flex-col items-center gap-4 p-8">
      <h1 className="text-lg font-semibold">로그인</h1>
      <button
        onClick={redirectToKakaoLogin}
        className="rounded-lg bg-[#FEE500] px-4 py-2 text-sm font-medium text-black/85"
      >
        카카오로 로그인
      </button>
    </div>
  );
}
