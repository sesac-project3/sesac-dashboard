import axios, { type AxiosResponse, type InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL } from "@/shared/config/env";

// ponytail: localStorage 토큰 저장 방식은 참고 프로젝트(invest/frontend) convention을 그대로 따름.
// httpOnly 쿠키로 바꾸는 건 보안 강화 시점에 별도 작업으로.
const ACCESS_TOKEN_KEY = "accessToken";
const REFRESH_TOKEN_KEY = "refreshToken";
export const AUTH_TOKEN_CHANGED_EVENT = "auth-token-changed";

type RetryableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

const base = axios.create({ baseURL: API_BASE_URL, timeout: 10000 });

export const getAccessToken = () =>
  typeof window === "undefined" ? null : localStorage.getItem(ACCESS_TOKEN_KEY);

export const setTokens = (accessToken: string, refreshToken: string) => {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED_EVENT));
};

export const clearTokens = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED_EVENT));
};

base.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

// REST 401 인터셉터와 StockWebSocketProvider(소켓이 1008 "invalid/expired access token"으로
// 닫혔을 때) 양쪽에서 같은 갱신 절차를 타야 해서 함수로 뽑음.
export async function refreshAccessToken(): Promise<string> {
  const refreshToken = typeof window === "undefined" ? null : localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    clearTokens();
    throw new ApiError("리프레시 토큰이 없습니다.");
  }
  try {
    // 백엔드는 모든 응답을 ApiResponse 봉투({ data: ... })로 감싼다
    const refreshResponse = await axios.post<ApiEnvelope<{ accessToken: string; refreshToken: string }>>(
      `${API_BASE_URL}/auth/refresh`,
      { refreshToken },
    );
    const data = unwrapApiResponse(refreshResponse);
    if (!data) throw new ApiError("토큰 갱신 응답이 비어 있습니다.", refreshResponse.status);
    setTokens(data.accessToken, data.refreshToken);
    return data.accessToken;
  } catch (refreshError) {
    clearTokens();
    throw refreshError;
  }
}

base.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as RetryableRequestConfig | undefined;
    const hasRefreshToken =
      typeof window !== "undefined" && !!localStorage.getItem(REFRESH_TOKEN_KEY);
    if (error.response?.status !== 401 || !original || original._retry || !hasRefreshToken) {
      if (error.response?.status === 401) clearTokens();
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      const accessToken = await refreshAccessToken();
      original.headers.set("Authorization", `Bearer ${accessToken}`);
      return base(original);
    } catch (refreshError) {
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

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function unwrapApiResponse<T>(response: AxiosResponse<ApiEnvelope<T>>): T {
  const body = response.data;
  if (!body.success) {
    throw new ApiError(body.message, response.status, body.code);
  }
  return body.data as T;
}

export default base;
