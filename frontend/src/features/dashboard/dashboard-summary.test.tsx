import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { DashboardMetrics } from "./dashboard-metrics";
import { DashboardSummary } from "./dashboard-summary";
import type { DiaryDay } from "@/lib/api/types";

describe("DashboardSummary", () => {
  it("renders day metrics, calorie target, meals today and fallback actions", () => {
    const html = renderToStaticMarkup(
      <DashboardSummary
        diaryDay={diaryDay}
        error={null}
        isLoading={false}
        metrics={metrics}
        onRefresh={vi.fn()}
      />,
    );

    expect(html).toContain("Калории съедено");
    expect(html).toContain("Цель калорий");
    expect(html).toContain("Приёмы пищи");
    expect(html).toContain("≈");
    expect(html).toContain("Обед");
    expect(html).toContain("Добавить еду вручную");
    expect(html).toContain("Добавить через Scan");
  });
});

const metrics: DashboardMetrics = {
  caloriesConsumed: 399,
  calorieTarget: 2475,
  protein: 35.9,
  fat: 4.1,
  carbs: 50.8,
  mealsToday: 1,
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
      items: [
        {
          id: "item-1",
          food_id: "food-1",
          food_name_snapshot: "Рис",
          food_source_reference_snapshot: "demo",
          mass_g: "180",
          calories: "234",
          protein: "4.9",
          fat: "0.5",
          carbs: "50.8",
          micronutrient_snapshot: {},
          nutrient_snapshot: {},
          source: "manual",
          confidence: null,
          manually_corrected: true,
          created_at: "2026-08-19T12:30:00Z",
          updated_at: "2026-08-19T12:30:00Z",
        },
      ],
      created_at: "2026-08-19T12:30:00Z",
      updated_at: "2026-08-19T12:30:00Z",
    },
  ],
};
