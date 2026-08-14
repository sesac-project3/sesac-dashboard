import base, { type ApiEnvelope } from "@/shared/api/base";

export interface TelegramStatusResponse {
  linked: boolean;
  botUsername: string;
  notifyMorning: boolean;
  notifyEvening: boolean;
  notifyAlert: boolean;
}

export interface TelegramLinkCodeResponse {
  linkCode: string;
  botUsername: string;
}

export interface TelegramSettingsPayload {
  notifyMorning: boolean;
  notifyEvening: boolean;
  notifyAlert: boolean;
}

export const getTelegramStatus = () =>
  base.get<ApiEnvelope<TelegramStatusResponse>>("/telegram/status").then((res) => res.data.data!);

export const generateTelegramLinkCode = () =>
  base.post<ApiEnvelope<TelegramLinkCodeResponse>>("/telegram/link-code").then((res) => res.data.data!);

export const updateTelegramSettings = (payload: TelegramSettingsPayload) =>
  base.put<ApiEnvelope<string>>("/telegram/settings", payload).then((res) => res.data.data!);

export const disconnectTelegram = () =>
  base.delete<ApiEnvelope<string>>("/telegram/disconnect").then((res) => res.data.data!);
