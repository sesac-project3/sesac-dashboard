import axios, { type InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL } from "@/shared/config/env";

// ponytail: localStorage 토큰 저장 방식은 참고 프로젝트(invest/frontend) convention을 그대로 따름.
// httpOnly 쿠키로 바꾸는 건 보안 강화 시점에 별도 작업으로.
const ACCESS_TOKEN_KEY = "accessToken";
const REFRESH_TOKEN_KEY = "refreshToken";

type RetryableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

const base = axios.create({ baseURL: API_BASE_URL, timeout: 10000 });

export const getAccessToken = () =>
  typeof window === "undefined" ? null : localStorage.getItem(ACCESS_TOKEN_KEY);

export const setTokens = (accessToken: string, refreshToken: string) => {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
};

export const clearTokens = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
};

base.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

base.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as RetryableRequestConfig | undefined;
    const refreshToken =
      typeof window === "undefined" ? null : localStorage.getItem(REFRESH_TOKEN_KEY);

    if (error.response?.status !== 401 || !original || original._retry || !refreshToken) {
      if (error.response?.status === 401) clearTokens();
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      // 백엔드는 모든 응답을 ApiResponse 봉투({ data: ... })로 감싼다
      const { data } = await axios.post<ApiEnvelope<{ accessToken: string; refreshToken: string }>>(
        `${API_BASE_URL}/auth/refresh`,
        { refreshToken },
      );
      setTokens(data.data!.accessToken, data.data!.refreshToken);
      original.headers.set("Authorization", `Bearer ${data.data!.accessToken}`);
      return base(original);
    } catch (refreshError) {
      clearTokens();
      return Promise.reject(refreshError);
    }
  },
);

// 백엔드 공통 응답 포맷 (backend/app/common/response.py ApiResponse와 1:1 대응)
export interface ApiEnvelope<T> {
  success: boolean;
  status: number;
  code: string;
  message: string;
  data: T | null;
  timestamp: string;
}

export default base;
