// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/errors";
import { PasswordForm } from "./password-form";
import { PasswordResetRequestForm } from "./password-reset-request-form";

vi.mock("@/lib/api/auth", () => ({ authApi: {
  requestPasswordReset: vi.fn(), resetPassword: vi.fn(), changePassword: vi.fn(),
} }));

beforeEach(() => {
  cleanup();
  vi.resetAllMocks();
  window.history.replaceState({}, "", "/auth/password/reset");
});

describe("password recovery", () => {
  it("uses a generic response and clears email after a reset request", async () => {
    vi.mocked(authApi.requestPasswordReset).mockResolvedValue({ code: "password_reset_if_account_exists" });
    const user = userEvent.setup();
    render(<PasswordResetRequestForm />);
    await user.type(screen.getByLabelText("Email"), "unknown@example.test");
    await user.click(screen.getByRole("button", { name: "Отправить ссылку" }));
    expect(authApi.requestPasswordReset).toHaveBeenCalledWith("unknown@example.test");
    expect(screen.getByRole("status").textContent).toContain("Если подтверждённый аккаунт существует");
    expect((screen.getByLabelText("Email") as HTMLInputElement).value).toBe("");
  });

  it("rejects missing tokens without sending a reset", () => {
    render(<PasswordForm mode="reset" />);
    expect(screen.getByRole("alert").textContent).toContain("отсутствуют данные");
    expect((screen.getByRole("button", { name: "Установить пароль" }) as HTMLButtonElement).disabled).toBe(true);
    expect(authApi.resetPassword).not.toHaveBeenCalled();
  });

  it("checks confirmation then consumes the link only on a successful submit", async () => {
    window.history.replaceState({}, "", "/auth/password/reset?token_id=id&token=secret");
    vi.mocked(authApi.resetPassword).mockResolvedValue({ code: "password_reset_complete" });
    const user = userEvent.setup();
    render(<PasswordForm mode="reset" />);
    await user.type(screen.getByLabelText("Новый пароль"), "Strong-password123!");
    await user.type(screen.getByLabelText("Повторите новый пароль"), "Different-password!");
    await user.click(screen.getByRole("button", { name: "Установить пароль" }));
    expect(screen.getByRole("alert").textContent).toBe("Пароли не совпадают.");
    expect(authApi.resetPassword).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText("Повторите новый пароль"));
    await user.type(screen.getByLabelText("Повторите новый пароль"), "Strong-password123!");
    await user.click(screen.getByRole("button", { name: "Установить пароль" }));
    expect(authApi.resetPassword).toHaveBeenCalledWith({
      token_id: "id", token: "secret", new_password: "Strong-password123!",
    });
    expect(screen.getByRole("status").textContent).toContain("Войдите с новым паролем");
    expect(window.location.search).toBe("");
    expect((screen.getByLabelText("Новый пароль") as HTMLInputElement).value).toBe("");
    expect((screen.getByRole("button", { name: "Установить пароль" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows an expired-link error and offers another reset request", async () => {
    window.history.replaceState({}, "", "/auth/password/reset?token_id=id&token=expired");
    vi.mocked(authApi.resetPassword).mockRejectedValue(new ApiError({ status: 403, code: "invalid_or_expired_token", details: null }));
    const user = userEvent.setup();
    render(<PasswordForm mode="reset" />);
    await user.type(screen.getByLabelText("Новый пароль"), "Strong-password123!");
    await user.type(screen.getByLabelText("Повторите новый пароль"), "Strong-password123!");
    await user.click(screen.getByRole("button", { name: "Установить пароль" }));
    expect(screen.getByRole("alert").textContent).toContain("Ссылка недействительна");
    expect(screen.getByRole("link", { name: "Отправить ссылку" }).getAttribute("href")).toBe("/forgot-password");
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("changes the password with the current password and clears secret fields", async () => {
    vi.mocked(authApi.changePassword).mockResolvedValue({ code: "password_changed" });
    const user = userEvent.setup();
    render(<PasswordForm mode="change" />);
    await user.type(screen.getByLabelText("Текущий пароль"), "Old-password123!");
    await user.type(screen.getByLabelText("Новый пароль"), "New-password123!");
    await user.type(screen.getByLabelText("Повторите новый пароль"), "New-password123!");
    await user.click(screen.getByRole("button", { name: "Изменить пароль" }));
    expect(authApi.changePassword).toHaveBeenCalledWith("Old-password123!", "New-password123!");
    expect(screen.getByRole("status").textContent).toContain("текущая сессия сохранена");
    expect((screen.getByLabelText("Текущий пароль") as HTMLInputElement).value).toBe("");
  });

  it("disables submissions while a request is in progress and permits retry after failure", async () => {
    let rejectRequest: ((error: Error) => void) | undefined;
    vi.mocked(authApi.requestPasswordReset).mockImplementation(() => new Promise((_resolve, reject) => { rejectRequest = reject; }));
    const user = userEvent.setup();
    render(<PasswordResetRequestForm />);
    await user.type(screen.getByLabelText("Email"), "person@example.test");
    await user.click(screen.getByRole("button", { name: "Отправить ссылку" }));
    expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(true);
    rejectRequest?.(new Error("Network unavailable"));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Network unavailable"));
    expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(false);
  });
});
