// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "@/lib/api/auth";

import { RegisterForm } from "./register-form";

vi.mock("@/lib/api/auth", () => ({
  authApi: {
    register: vi.fn(),
    resendVerification: vi.fn(),
  },
}));

describe("RegisterForm", () => {
  beforeEach(() => {
    vi.mocked(authApi.register).mockReset();
    vi.mocked(authApi.resendVerification).mockReset();
  });

  it("waits for email verification instead of opening the protected dashboard", async () => {
    vi.mocked(authApi.register).mockResolvedValue({
      code: "registration_pending_verification",
      user: {
        id: "user-1",
        email: "user@example.com",
        is_active: false,
        roles: ["user"],
        profile: {
          id: "profile-1",
          user_id: "user-1",
          display_name: "Тест",
          preferred_language: "ru",
          created_at: "2026-08-26T10:00:00Z",
          updated_at: "2026-08-26T10:00:00Z",
        },
        created_at: "2026-08-26T10:00:00Z",
        updated_at: "2026-08-26T10:00:00Z",
      },
    });

    render(<RegisterForm />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Пароль"), {
      target: { value: "correct-password" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Создать аккаунт" }).closest("form")!);

    await waitFor(() => {
      expect(authApi.register).toHaveBeenCalledWith(
        expect.objectContaining({ email: "user@example.com" }),
      );
    });
    expect(await screen.findByRole("heading", { name: "Подтвердите email" })).toBeTruthy();
    expect(screen.getByText("user@example.com")).toBeTruthy();
    expect(screen.queryByText("Обзор дня")).toBeNull();
  });
});
