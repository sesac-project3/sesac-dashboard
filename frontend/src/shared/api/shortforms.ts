import base, { type ApiEnvelope } from "@/shared/api/base";
import type { Shortform } from "@/entities/shortform/types";

export const getShortforms = () =>
  base.get<ApiEnvelope<Shortform[]>>("/shortforms").then((res) => res.data.data ?? []);

export const toggleShortformLike = (id: number) =>
  base
    .post<ApiEnvelope<{ liked: boolean; likeCount: number }>>(`/shortforms/${id}/like`)
    .then((res) => res.data.data!);
