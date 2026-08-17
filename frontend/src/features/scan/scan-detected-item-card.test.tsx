import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { FoodScanDetectedItem } from "@/lib/api/types";

import { ScanDetectedItemCard } from "./scan-detected-item-card";

describe("ScanDetectedItemCard", () => {
  it("shows model uncertainty, editable mass and nutrients for a detected item", () => {
    const html = renderToStaticMarkup(
      <ScanDetectedItemCard
        foodOptions={[]}
        foodQuery=""
        isSaving={false}
        isSearching={false}
        item={detectedRice}
        massDraft="180"
        onFoodQueryChange={vi.fn()}
        onFoodSearch={vi.fn()}
        onMassDraftChange={vi.fn()}
        onRemove={vi.fn()}
        onSaveMass={vi.fn()}
        onSelectFood={vi.fn()}
      />,
    );

    expect(html).toContain("Рис");
    expect(html).toContain("≈ 180 г");
    expect(html).toContain("155 г–205 г");
    expect(html).toContain("234");
    expect(html).toContain("ккал");
    expect(html).toContain("Масса после проверки, г");
  });
});

const detectedRice: FoodScanDetectedItem = {
  id: "item-1",
  label: "rice",
  confidence: "0.92",
  food_id: "food-1",
  food: {
    id: "food-1",
    name: "Rice",
    name_ru: "Рис",
    name_en: "Rice",
  },
  mass_g: "180",
  manual_mass_g: null,
  portion_estimate: {
    estimated_volume: "210",
    estimated_mass: "180",
    confidence: "0.62",
    min_estimate: "155",
    max_estimate: "205",
    method: "density_table",
  },
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
