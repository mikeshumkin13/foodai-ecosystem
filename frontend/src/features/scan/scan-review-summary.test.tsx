import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { FoodScanDetectedItem } from "@/lib/api/types";

import { ScanReviewSummary } from "./scan-review-summary";

describe("ScanReviewSummary", () => {
  it("renders totals and the confirmation action for active detected items", () => {
    const html = renderToStaticMarkup(
      <ScanReviewSummary
        addMass="100"
        addOptions={[]}
        addQuery=""
        canConfirm={true}
        isAddingItem={false}
        isConfirming={false}
        isSearchingAddFood={false}
        items={[detectedRice, detectedChicken]}
        loggedAt="2026-08-17T12:30"
        mealType="lunch"
        onAddItem={vi.fn()}
        onAddMassChange={vi.fn()}
        onAddQueryChange={vi.fn()}
        onConfirm={vi.fn()}
        onLoggedAtChange={vi.fn()}
        onMealTypeChange={vi.fn()}
        onSearchAddFood={vi.fn()}
        onSelectedAddFoodChange={vi.fn()}
        selectedAddFoodId=""
      />,
    );

    expect(html).toContain("Итог перед дневником");
    expect(html).toContain("399");
    expect(html).toContain("Подтвердить и открыть дневник");
    expect(html).toContain("Добавить отсутствующий продукт");
  });
});

const detectedRice: FoodScanDetectedItem = {
  id: "item-1",
  label: "rice",
  confidence: "0.92",
  food_id: "food-1",
  food: null,
  mass_g: "180",
  manual_mass_g: null,
  portion_estimate: null,
  calories: "234",
  protein: "4.9",
  fat: "0.5",
  carbs: "50.8",
  nutrient_snapshot: {},
  micronutrient_snapshot: {},
  source: "vision",
  is_removed: false,
  manually_corrected: false,
  created_at: "2026-08-17T10:00:00Z",
  updated_at: "2026-08-17T10:00:00Z",
};

const detectedChicken: FoodScanDetectedItem = {
  ...detectedRice,
  id: "item-2",
  label: "chicken",
  calories: "165",
  protein: "31",
  fat: "3.6",
  carbs: "0",
};
