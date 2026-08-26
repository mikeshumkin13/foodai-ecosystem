// @vitest-environment jsdom

import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "@/lib/api/auth";

import { EmailVerificationPanel } from "./email-verification-panel";

vi.mock("@/lib/api/auth", () => ({
  authApi: {
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
  },
}));

describe("EmailVerificationPanel", () => {
  beforeEach(() => {
    vi.mocked(authApi.verifyEmail).mockReset();
    vi.mocked(authApi.resendVerification).mockReset();
    window.history.replaceState({}, "", "/auth/email/verify");
  });

  it("verifies the one-time token from the email link", async () => {
    window.history.replaceState(
      {},
      "",
      "/auth/email/verify?token_id=token-id&token=secret-token",
    );
    vi.mocked(authApi.verifyEmail).mockResolvedValue({ code: "email_verified" });

    render(<EmailVerificationPanel />);

    await waitFor(() => {
      expect(authApi.verifyEmail).toHaveBeenCalledTimes(1);
    });
    expect(authApi.verifyEmail).toHaveBeenCalledWith({
      token_id: "token-id",
      token: "secret-token",
    });
    expect(await screen.findByRole("heading", { name: "Email подтверждён" })).toBeTruthy();
  });

  it("does not call the backend when the link has no token", async () => {
    render(<EmailVerificationPanel />);

    expect(await screen.findByRole("heading", { name: "Ссылка не сработала" })).toBeTruthy();
    expect(authApi.verifyEmail).not.toHaveBeenCalled();
  });
});
