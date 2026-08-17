import { clearCsrfToken } from "@/lib/csrf";

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

export const authApi = {
  csrf: ensureCsrfToken,
  register(payload: RegisterPayload) {
    return apiRequest<AuthUserResponse>("/api/v1/auth/register/", {
      method: "POST",
      body: payload,
    });
  },
  login(payload: LoginPayload) {
    return apiRequest<AuthUserResponse>("/api/v1/auth/login/", {
      method: "POST",
      body: payload,
    });
  },
  async logout() {
    const response = await apiRequest<ApiCodeResponse>("/api/v1/auth/logout/", {
      method: "POST",
    });
    clearCsrfToken();
    return response;
  },
  refresh() {
    return apiRequest<AuthUserResponse>("/api/v1/auth/refresh/", {
      method: "POST",
    });
  },
  me() {
    return apiRequest<UserSummary>("/api/v1/auth/me/");
  },
};
