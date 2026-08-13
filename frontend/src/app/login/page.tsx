import { redirect } from "next/navigation";

// 온보딩+카카오 로그인 CTA는 이제 홈(/)이 로그아웃 상태일 때 보여준다(HomeGate).
// /login은 그 전 위치를 기억하고 있을 수 있는 링크/북마크를 위해 홈으로 보내기만 한다.
export default function LoginPage() {
  redirect("/");
}
