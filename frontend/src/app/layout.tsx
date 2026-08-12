import type { Metadata } from "next";
import { pretendard } from "./fonts";
import AppHeader from "@/widgets/header/AppHeader";
import BottomTabBar from "@/widgets/bottom-tab/BottomTabBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "sesac-dashboard",
  description: "AI 기반 국내주식 투자 인사이트 플랫폼",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className={`${pretendard.variable} h-dvh antialiased`}>
      {/* h-dvh + overflow-hidden: 바깥(body) 스크롤을 없애서, 페이지마다 자기 영역
          안에서만 스크롤하게 한다(숏폼 풀스크린 스와이프 피드가 대표적 이유). */}
      <body className="flex h-dvh flex-col overflow-hidden font-sans">
        <AppHeader />
        {/* min-h-0: flex item은 기본적으로 내용물보다 작아지지 않으려 해서 필요
            (flexbox 흔한 함정). overflow-y-auto: 일반 페이지 기본 스크롤 담당. */}
        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
        <BottomTabBar />
      </body>
    </html>
  );
}
