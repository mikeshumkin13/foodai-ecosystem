// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { profileApi } from "@/lib/api/profile";
import type { NutritionProfile } from "@/lib/api/types";

import { NutritionProfileForm } from "./nutrition-profile-form";

vi.mock("@/lib/api/profile", () => ({
  profileApi: {
    getCurrentNutritionProfile: vi.fn(),
    updateNutritionProfile: vi.fn(),
  },
}));

describe("NutritionProfileForm", () => {
  beforeEach(() => {
    vi.mocked(profileApi.getCurrentNutritionProfile).mockReset();
    vi.mocked(profileApi.updateNutritionProfile).mockReset();
  });

  it("loads and saves the own profile only after explicit consent", async () => {
    vi.mocked(profileApi.getCurrentNutritionProfile).mockResolvedValue(profile);
    vi.mocked(profileApi.updateNutritionProfile).mockResolvedValue({
      ...profile,
      goal: "lose_weight",
      height_cm: 181,
      mass_kg: "82.40",
      consent_granted_at: "2026-08-26T10:30:00Z",
    });

    render(<NutritionProfileForm />);

    const goal = await screen.findByLabelText("Цель");
    const saveButton = screen.getByRole("button", { name: "Сохранить" });
    expect(saveButton.hasAttribute("disabled")).toBe(true);

    fireEvent.change(goal, { target: { value: "lose_weight" } });
    fireEvent.change(screen.getByLabelText("Рост, см"), { target: { value: "181" } });
    fireEvent.change(screen.getByLabelText("Масса, кг"), { target: { value: "82.40" } });
    fireEvent.click(screen.getByLabelText("Я согласен сохранить эти данные в nutrition profile."));
    fireEvent.submit(saveButton.closest("form")!);

    await waitFor(() => {
      expect(profileApi.updateNutritionProfile).toHaveBeenCalledWith(
        "profile-1",
        expect.objectContaining({
          goal: "lose_weight",
          height_cm: 181,
          mass_kg: "82.40",
          consent_accepted: true,
        }),
      );
    });
    expect(await screen.findByText("Профиль питания сохранён.")).toBeTruthy();
  });
});

const profile: NutritionProfile = {
  id: "profile-1",
  user_id: "user-1",
  goal: "maintain_weight",
  height_cm: null,
  mass_kg: null,
  age_category: "prefer_not_to_say",
  activity_level: "moderate",
  preferred_units: "metric",
  dietary_preferences: [],
  consent_version: "nutrition_profile_mvp_v1",
  consent_granted_at: null,
  consent_revoked_at: null,
  created_at: "2026-08-26T10:00:00Z",
  updated_at: "2026-08-26T10:00:00Z",
};
