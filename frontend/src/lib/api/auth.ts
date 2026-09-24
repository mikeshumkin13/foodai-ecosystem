import { clearCsrfToken } from "@/lib/csrf";
import { notifyAuthenticationRequired } from "@/lib/auth/session-events";

import { apiRequest, ensureCsrfToken } from "./client";
import type { ApiCodeResponse, AuthUserResponse, LocaleCode, UserSummary } from "./types";

export type RegisterPayload = {
  email: string;
  password: string;
  display_name?: string;
  preferred_language?: LocaleCode;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type EmailVerificationPayload = {
  token_id: string;
  token: string;
};

export const authApi = {
  csrf: ensureCsrfToken,
  register(payload: RegisterPayload) {
    return apiRequest<AuthUserResponse>("/api/v1/auth/register/", {
      method: "POST",
      body: payload,
    });
  },
  verifyEmail(payload: EmailVerificationPayload) {
    return apiRequest<ApiCodeResponse>("/api/v1/auth/email/verify/", {
      method: "POST",
      body: payload,
    });
  },
  resendVerification(email: string) {
    return apiRequest<ApiCodeResponse>("/api/v1/auth/email/resend/", {
      method: "POST",
      body: { email },
    });
  },
  requestPasswordReset(email: string) {
    return apiRequest<ApiCodeResponse>("/api/v1/auth/password/reset/request/", {
      method: "POST", body: { email },
    });
  },
  async resetPassword(payload: EmailVerificationPayload & { new_password: string }) {
    const response = await apiRequest<ApiCodeResponse>("/api/v1/auth/password/reset/confirm/", {
      method: "POST", body: payload,
    });
    clearCsrfToken();
    notifyAuthenticationRequired();
    return response;
  },
  async changePassword(currentPassword: string, newPassword: string) {
    const response = await apiRequest<ApiCodeResponse>("/api/v1/auth/password/change/", {
      method: "POST", body: { current_password: currentPassword, new_password: newPassword },
    });
    clearCsrfToken();
    return response;
  },
  async login(payload: LoginPayload) {
    const response = await apiRequest<AuthUserResponse>("/api/v1/auth/login/", {
      method: "POST",
      body: payload,
    });
    clearCsrfToken();
    return response;
  },
  async logout() {
    const response = await apiRequest<ApiCodeResponse>("/api/v1/auth/logout/", {
      method: "POST",
    });
    clearCsrfToken();
    return response;
  },
  async refresh() {
    const response = await apiRequest<AuthUserResponse>("/api/v1/auth/refresh/", {
      method: "POST",
    });
    clearCsrfToken();
    return response;
  },
  me() {
    return apiRequest<UserSummary>("/api/v1/auth/me/");
  },
};
