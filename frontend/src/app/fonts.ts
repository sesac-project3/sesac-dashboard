import localFont from "next/font/local";

// DESIGN_SPEC.md §5.1: Pretendard 단일 타이포그래피, 장식용 serif/mono 사용 금지.
// npm pretendard 패키지의 variable 폰트 하나로 전체 weight(45~920) 커버.
export const pretendard = localFont({
  src: "../../node_modules/pretendard/dist/web/variable/woff2/PretendardVariable.woff2",
  display: "swap",
  weight: "45 920",
  variable: "--font-pretendard",
});
