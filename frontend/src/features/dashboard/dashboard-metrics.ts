import type { DiaryDay, NutritionProfile } from "@/lib/api/types";

export type DashboardMetrics = {
  caloriesConsumed: number;
  calorieTarget: number | null;
  protein: number;
  fat: number;
  carbs: number;
  mealsToday: number;
};

const activityKcalPerKg: Record<string, number> = {
  sedentary: 25,
  light: 28,
  moderate: 31,
  active: 34,
  very_active: 37,
};

const goalAdjustmentKcal: Record<string, number> = {
  maintain_weight: 0,
  improve_habits: 0,
  lose_weight: -300,
  gain_weight: 250,
};

export function getDashboardMetrics(
  diaryDay: DiaryDay | null,
  nutritionProfile: NutritionProfile | null,
): DashboardMetrics {
  return {
    caloriesConsumed: toNumber(diaryDay?.totals.calories),
    calorieTarget: estimateDailyCalorieTarget(nutritionProfile),
    protein: toNumber(diaryDay?.totals.protein),
    fat: toNumber(diaryDay?.totals.fat),
    carbs: toNumber(diaryDay?.totals.carbs),
    mealsToday: diaryDay?.meals.length ?? 0,
  };
}

export function estimateDailyCalorieTarget(profile: NutritionProfile | null): number | null {
  if (!profile || profile.age_category === "under_18") {
    return null;
  }

  const massKg = toNumber(profile.mass_kg);
  if (massKg <= 0) {
    return null;
  }

  const activityFactor = activityKcalPerKg[profile.activity_level] ?? activityKcalPerKg.moderate;
  const goalAdjustment = goalAdjustmentKcal[profile.goal] ?? 0;
  const estimatedTarget = massKg * activityFactor + goalAdjustment;
  const roundedTarget = Math.round(estimatedTarget / 25) * 25;

  return Math.max(roundedTarget, 1200);
}

function toNumber(value: string | number | null | undefined): number {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : 0;
}
