"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLoggedIn } from "@/shared/hooks/useLoggedIn";
import { logout } from "@/shared/api/auth";
import PageContainer from "@/shared/ui/PageContainer";
import Card from "@/shared/ui/Card";

// 내 정보(F-00 프로토타입). 카카오 프로필(닉네임 등)은 아직 백엔드가 저장/노출하지 않아서
// 가짜 값을 보여주지 않고 로그인 상태 + 로그아웃만 제공한다 — 다른 로그인 필요 기능(좋아요
// 등)과 같은 패턴: 로그인 안 했으면 홈(온보딩)으로 보낸다.
export default function ProfilePage() {
  const router = useRouter();
  const loggedIn = useLoggedIn();

  useEffect(() => {
    if (loggedIn === false) router.replace("/login");
  }, [loggedIn, router]);

  if (!loggedIn) return null;

  return (
    <PageContainer>
      <h1 className="my-4 text-[18px] font-semibold text-heading">내 정보</h1>
      <Card className="flex flex-col gap-1">
        <p className="text-[14px] font-medium text-heading">카카오 계정으로 로그인됨</p>
        <p className="text-[13px] text-caption">세싹대시보드를 이용해주셔서 감사합니다.</p>
      </Card>
      <button
        onClick={logout}
        className="mt-4 flex h-[52px] w-full items-center justify-center rounded-full border border-border text-[15px] font-medium text-danger transition active:scale-[0.98]"
      >
        로그아웃
      </button>
    </PageContainer>
  );
}
