// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { AccountSecurityPanel } from "./account-security-panel";

const { logout, replace } = vi.hoisted(() => ({ logout: vi.fn(), replace: vi.fn() }));
vi.mock("@/components/auth-session-provider", () => ({ useAuthSession: () => ({ logout }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("./password-form", () => ({ PasswordForm: () => <h2>Account security</h2> }));
beforeEach(() => { cleanup(); vi.resetAllMocks(); });

it("exposes logout in the profile without the desktop sidebar", async () => {
  logout.mockResolvedValue(undefined);
  render(<AccountSecurityPanel />);
  await userEvent.click(screen.getByRole("button", { name: "Выйти" }));
  expect(logout).toHaveBeenCalledOnce();
  expect(replace).toHaveBeenCalledWith("/login");
});

it("does not claim logout succeeded when the server is unavailable", async () => {
  logout.mockRejectedValue(new Error("Server unavailable"));
  render(<AccountSecurityPanel />);
  await userEvent.click(screen.getByRole("button", { name: "Выйти" }));
  expect(screen.getByRole("alert").textContent).toBe("Server unavailable");
  expect(replace).not.toHaveBeenCalled();
});
