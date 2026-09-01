import { apiRequest } from "./client";
import type { AICoachResponse, AICoachSettings } from "./types";

export type AICoachAskPayload = {
  message: string;
  date?: string;
  store_response?: boolean;
};

export const aiCoachApi = {
  getSettings() {
    return apiRequest<AICoachSettings>("/api/v1/ai/coach/settings/");
  },
  updateHistoryConsent(enabled: boolean) {
    return apiRequest<AICoachSettings>("/api/v1/ai/coach/settings/", {
      method: "PATCH",
      body: enabled
        ? { chat_history_consent_accepted: true }
        : { chat_history_consent_revoked: true },
    });
  },
  ask(payload: AICoachAskPayload) {
    return apiRequest<AICoachResponse>("/api/v1/ai/coach/ask/", {
      method: "POST",
      body: payload,
    });
  },
};
