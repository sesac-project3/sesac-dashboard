import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Header from "@/widgets/header/Header";
import BottomTab from "@/widgets/bottom-tab/BottomTab";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "sesac-dashboard",
  description: "AI 기반 국내주식 투자 인사이트 플랫폼",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-dvh antialiased`}
    >
      {/* h-dvh + overflow-hidden으로 바깥(body) 스크롤을 아예 없앤다.
          이게 없으면 안쪽(숏폼 스와이프 등) 스크롤 영역과 바깥 페이지 스크롤이
          동시에 생겨서 스냅이 살짝 어긋나 다음 카드가 삐져나와 보인다. */}
      <body className="flex h-dvh flex-col overflow-hidden">
        <Header />
        {/* min-h-0: flex item은 기본적으로 내용물보다 작아지지 않으려 해서, 이게 없으면
            자식의 overflow-y-scroll이 부모 높이를 넘어서도 잘리지 않는다(flexbox 흔한 함정).
            overflow-y-auto: body가 더 이상 안 스크롤되니, 콘텐츠 긴 일반 페이지들의
            기본 스크롤은 여기서 담당한다. 숏폼 페이지는 자기 안에서 정확히 h-full로
            꽉 채우고 직접 스크롤하니 여기 스크롤은 발동 안 함. */}
        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
        <BottomTab />
      </body>
    </html>
  );
}
