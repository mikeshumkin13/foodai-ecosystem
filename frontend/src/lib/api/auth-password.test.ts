// @vitest-environment jsdom

import { beforeEach, expect, it, vi } from "vitest";
import { authApi } from "./auth";
import { apiRequest } from "./client";
import { clearCsrfToken } from "@/lib/csrf";
import { notifyAuthenticationRequired } from "@/lib/auth/session-events";

vi.mock("./client", () => ({ apiRequest: vi.fn(), ensureCsrfToken: vi.fn() }));
vi.mock("@/lib/csrf", () => ({ clearCsrfToken: vi.fn() }));
vi.mock("@/lib/auth/session-events", () => ({ notifyAuthenticationRequired: vi.fn() }));
beforeEach(() => vi.resetAllMocks());

it("refreshes the cached CSRF token after password change without logging out", async () => {
  vi.mocked(apiRequest).mockResolvedValue({ code: "password_changed" });
  await authApi.changePassword("current", "new");
  expect(apiRequest).toHaveBeenCalledWith("/api/v1/auth/password/change/", {
    method: "POST", body: { current_password: "current", new_password: "new" },
  });
  expect(clearCsrfToken).toHaveBeenCalledOnce();
  expect(notifyAuthenticationRequired).not.toHaveBeenCalled();
});

it("invalidates the client session state after password reset", async () => {
  vi.mocked(apiRequest).mockResolvedValue({ code: "password_reset_complete" });
  await authApi.resetPassword({ token_id: "id", token: "token", new_password: "new" });
  expect(clearCsrfToken).toHaveBeenCalledOnce();
  expect(notifyAuthenticationRequired).toHaveBeenCalledOnce();
});

it("does not invalidate the current session on a rejected reset", async () => {
  vi.mocked(apiRequest).mockRejectedValue(new Error("expired"));
  await expect(authApi.resetPassword({ token_id: "id", token: "token", new_password: "new" })).rejects.toThrow("expired");
  expect(notifyAuthenticationRequired).not.toHaveBeenCalled();
  expect(clearCsrfToken).not.toHaveBeenCalled();
});
