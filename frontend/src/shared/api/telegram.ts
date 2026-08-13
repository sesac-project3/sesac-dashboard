import base, { type ApiEnvelope } from "@/shared/api/base";

export interface TelegramStatusResponse {
  linked: boolean;
  botUsername: string;
}

export interface TelegramLinkCodeResponse {
  linkCode: string;
  botUsername: string;
}

export const getTelegramStatus = () =>
  base.get<ApiEnvelope<TelegramStatusResponse>>("/telegram/status").then((res) => res.data.data!);

export const generateTelegramLinkCode = () =>
  base.post<ApiEnvelope<TelegramLinkCodeResponse>>("/telegram/link-code").then((res) => res.data.data!);
