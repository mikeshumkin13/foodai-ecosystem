import { describe, expect, it } from "vitest";

import type { DiaryDay, NutritionProfile } from "@/lib/api/types";

import { estimateDailyCalorieTarget, getDashboardMetrics } from "./dashboard-metrics";

describe("dashboard metrics", () => {
  it("builds consumed nutrients, meals today and estimated calorie target", () => {
    const metrics = getDashboardMetrics(diaryDay, nutritionProfile);

    expect(metrics.caloriesConsumed).toBe(399);
    expect(metrics.protein).toBe(35.9);
    expect(metrics.fat).toBe(4.1);
    expect(metrics.carbs).toBe(50.8);
    expect(metrics.mealsToday).toBe(1);
    expect(metrics.calorieTarget).toBe(2475);
  });

  it("does not estimate a target for under-18 profile", () => {
    expect(
      estimateDailyCalorieTarget({
        ...nutritionProfile,
        age_category: "under_18",
      }),
    ).toBeNull();
  });
});

const nutritionProfile: NutritionProfile = {
  id: "profile-1",
  user_id: "user-1",
  goal: "maintain_weight",
  height_cm: "181",
  mass_kg: "80.00",
  age_category: "30_39",
  activity_level: "moderate",
  preferred_units: "metric",
  dietary_preferences: [],
  consent_version: "nutrition_profile_mvp_v1",
  consent_granted_at: "2026-08-19T10:00:00Z",
  consent_revoked_at: null,
  created_at: "2026-08-19T10:00:00Z",
  updated_at: "2026-08-19T10:00:00Z",
};

const diaryDay: DiaryDay = {
  date: "2026-08-19",
  totals: {
    calories: "399",
    protein: "35.9",
    fat: "4.1",
    carbs: "50.8",
  },
  micronutrient_totals: {},
  meals: [
    {
      id: "meal-1",
      user_id: "user-1",
      meal_type: "lunch",
      logged_at: "2026-08-19T12:30:00Z",
      name: "Обед",
      items: [],
      created_at: "2026-08-19T12:30:00Z",
      updated_at: "2026-08-19T12:30:00Z",
    },
  ],
};
