import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <main className="flex-1">{children}</main>
        <BottomTab />
      </body>
    </html>
  );
}
