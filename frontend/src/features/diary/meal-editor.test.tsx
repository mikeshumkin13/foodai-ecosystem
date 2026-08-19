import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { Meal } from "@/lib/api/types";

import { MealEditor } from "./meal-editor";

describe("MealEditor", () => {
  it("renders a manual add flow without requiring AI Scan", () => {
    const html = renderToStaticMarkup(
      <MealEditor
        date="2026-08-19"
        isSaving={false}
        meal={null}
        onCancel={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(html).toContain("Ручное добавление");
    expect(html).toContain("Поиск еды");
    expect(html).toContain("Добавить продукт");
    expect(html).toContain("Сохранить приём пищи");
  });

  it("renders an existing meal for editing", () => {
    const html = renderToStaticMarkup(
      <MealEditor
        date="2026-08-19"
        isSaving={false}
        meal={meal}
        onCancel={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(html).toContain("Редактирование приёма пищи");
    expect(html).toContain("Рис");
    expect(html).toContain("180");
    expect(html).toContain("Обновить приём пищи");
  });
});

const meal: Meal = {
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
};
