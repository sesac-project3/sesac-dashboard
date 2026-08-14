import { API_BASE_URL } from "@/shared/config/env";
import { clearTokens } from "@/shared/api/base";

// 카카오 client id/secret은 프론트에 노출하지 않는다 — 백엔드가 인가코드 교환까지 전담하고
// 우리 서비스 JWT를 발급한 뒤 /login/complete로 리다이렉트한다 (PRODUCT.md ISSUE-001).
export const redirectToKakaoLogin = () => {
  window.location.href = `${API_BASE_URL}/auth/kakao/login`;
};

export const logout = () => {
  clearTokens();
  window.location.href = "/login";
};
