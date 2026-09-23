// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    cleanup();
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

  it("lets a previously registered user request a new link without exposing account existence", async () => {
    vi.mocked(authApi.resendVerification).mockResolvedValue({ code: "email_verification_sent" });
    render(<EmailVerificationPanel />);

    expect(await screen.findByRole("heading", { name: "Подтвердите email" })).toBeTruthy();
    expect(authApi.verifyEmail).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).toBeNull();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "pending@example.test");
    await user.click(screen.getByRole("button", { name: "Отправить письмо повторно" }));
    expect(authApi.resendVerification).toHaveBeenCalledWith("pending@example.test");
    expect(await screen.findByText("Если аккаунт ожидает подтверждения, новое письмо отправлено.")).toBeTruthy();
  });

  it("still rejects an incomplete verification link", async () => {
    window.history.replaceState({}, "", "/auth/email/verify?token_id=incomplete");
    render(<EmailVerificationPanel />);
    expect(await screen.findByRole("heading", { name: "Ссылка не сработала" })).toBeTruthy();
    expect(authApi.verifyEmail).not.toHaveBeenCalled();
  });
});
