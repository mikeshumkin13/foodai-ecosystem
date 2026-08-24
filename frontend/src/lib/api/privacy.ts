import { apiBlobRequest, apiRequest } from "./client";
import type {
  PrivacyConsentPayload,
  PrivacyDataSummary,
  PrivacyDeletionResponse,
  PrivacySettings,
} from "./types";

export const privacyApi = {
  summary() {
    return apiRequest<PrivacyDataSummary>("/api/v1/privacy/data-summary/");
  },
  consent() {
    return apiRequest<PrivacySettings>("/api/v1/privacy/consent/");
  },
  updateConsent(payload: PrivacyConsentPayload) {
    return apiRequest<PrivacySettings>("/api/v1/privacy/consent/", {
      method: "PATCH",
      body: payload,
    });
  },
  exportData() {
    return apiBlobRequest("/api/v1/privacy/export/");
  },
  deleteFoodPhoto(scanId: string) {
    return apiRequest<PrivacyDeletionResponse>(`/api/v1/privacy/food-photos/${scanId}/`, {
      method: "DELETE",
    });
  },
  deleteAiChatHistory() {
    return apiRequest<PrivacyDeletionResponse>("/api/v1/privacy/ai-chat-history/", {
      method: "DELETE",
    });
  },
  deleteAccount(currentPassword: string) {
    return apiRequest<PrivacyDeletionResponse>("/api/v1/privacy/account/", {
      method: "DELETE",
      body: { current_password: currentPassword },
    });
  },
};
