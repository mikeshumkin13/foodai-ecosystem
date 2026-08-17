import type { FoodScanDetectedItem, FoodSearchItem } from "@/lib/api/types";

export function formatDecimal(value: string | number | null | undefined, fractionDigits = 0): string {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) {
    return "0";
  }

  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: 0,
  }).format(numberValue);
}

export function formatGrams(value: string | number | null | undefined): string {
  return `${formatDecimal(value, 0)} г`;
}

export function formatApproximateGrams(value: string | number | null | undefined): string {
  return `≈ ${formatGrams(value)}`;
}

export function formatPercent(value: string | number | null | undefined): string {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) {
    return "0%";
  }

  return `${formatDecimal(numberValue * 100, 0)}%`;
}

export function getDetectedItemDisplayName(item: FoodScanDetectedItem): string {
  return item.food?.name_ru || item.food?.name || item.label;
}

export function getFoodSearchDisplayName(food: FoodSearchItem): string {
  return food.name_ru || food.name || food.name_en;
}

export function getMassDraftValue(item: FoodScanDetectedItem): string {
  return item.manual_mass_g ?? item.mass_g;
}

export function getPortionRangeLabel(item: FoodScanDetectedItem): string {
  if (!item.portion_estimate) {
    return "";
  }

  return `${formatGrams(item.portion_estimate.min_estimate)}–${formatGrams(
    item.portion_estimate.max_estimate,
  )}`;
}

export function getScanTotals(items: FoodScanDetectedItem[]) {
  return items
    .filter((item) => !item.is_removed)
    .reduce(
      (totals, item) => ({
        calories: totals.calories + Number(item.calories || 0),
        protein: totals.protein + Number(item.protein || 0),
        fat: totals.fat + Number(item.fat || 0),
        carbs: totals.carbs + Number(item.carbs || 0),
      }),
      { calories: 0, protein: 0, fat: 0, carbs: 0 },
    );
}
