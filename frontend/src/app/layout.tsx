import type { Metadata } from "next";
import { pretendard } from "./fonts";
import AppHeader from "@/widgets/header/AppHeader";
import BottomTabBar from "@/widgets/bottom-tab/BottomTabBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "ZStock - 쉽고 빠른 주식정보",
  description: "AI 기반 국내주식 투자 인사이트 플랫폼",
  icons: {
    icon: "/img/favicon/favicon.svg",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className={`${pretendard.variable} h-dvh antialiased`}>
      {/* h-dvh + overflow-hidden: 바깥(body) 스크롤을 없애서, 페이지마다 자기 영역
          안에서만 스크롤하게 한다(숏폼 풀스크린 스와이프 피드가 대표적 이유). */}
      <body className="flex h-dvh justify-center overflow-hidden bg-surface font-sans">
        {/* DESIGN_SPEC.md §0.2: "모바일 우선, 기본 콘텐츠 max-width 480px". 예전엔 이 제한이
            PageContainer(페이지 내부 콘텐츠)에만 걸려 있어서, 넓은 화면(데스크톱 브라우저 등)
            에서 헤더/하단 탭바는 풀블리드로 늘어나고 콘텐츠만 가운데 480px 칼럼에 떠 있는
            것처럼 보이는 문제가 있었다. 헤더/탭바까지 포함한 앱 셸 전체를 여기서 한 번에
            480px로 고정 — 480px 미만에서는 그대로 뷰포트 100%, 그 이상에서는 좌우로 bg-surface
            여백이 생기며 가운데 정렬된다. */}
        <div className="flex h-full w-full max-w-[480px] flex-col overflow-hidden bg-background">
          <AppHeader />
          {/* min-h-0: flex item은 기본적으로 내용물보다 작아지지 않으려 해서 필요
              (flexbox 흔한 함정). overflow-y-auto: 일반 페이지 기본 스크롤 담당.
              no-scrollbar: 스크롤 기능은 그대로 두고 브라우저 기본 스크롤바만 숨김
              (모바일 앱 느낌 — 데스크톱 브라우저에서 오른쪽에 굵은 스크롤바가 보이던 것 제거). */}
          <main className="no-scrollbar min-h-0 flex-1 overflow-y-auto">{children}</main>
          <BottomTabBar />
        </div>
      </body>
    </html>
  );
}
