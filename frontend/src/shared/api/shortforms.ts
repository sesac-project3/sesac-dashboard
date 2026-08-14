import base, { unwrapApiResponse, type ApiEnvelope } from "@/shared/api/base";
import type { Shortform } from "@/entities/shortform/types";

export const getShortforms = () =>
  base.get<ApiEnvelope<Shortform[]>>("/shortforms").then(unwrapApiResponse).then((data) => data ?? []);

export const toggleShortformLike = (id: number) =>
  base
    .post<ApiEnvelope<{ liked: boolean; likeCount: number }>>(`/shortforms/${id}/like`)
    .then(unwrapApiResponse);

// /shortforms 목록 자체는 Next 서버 컴포넌트가 캐시 걸어 부르기 때문에(모든 사용자가
// 공유하는 캐시라 로그인 토큰을 못 실음) liked는 항상 false로 온다. 로그인했으면
// 브라우저에서 토큰을 실어 따로 가져와 화면에 합친다 — ShortformFeed 참고.
export const getLikedShortformIds = () =>
  base.get<ApiEnvelope<number[]>>("/shortforms/liked-ids").then(unwrapApiResponse).then((data) => data ?? []);
