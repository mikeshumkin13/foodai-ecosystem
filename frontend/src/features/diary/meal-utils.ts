import type { Meal, MealItem, MealType } from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

import { formatDecimal } from "../scan/scan-format";

const copy = messages.ru;

export type MealNutritionTotals = {
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
};

export function getMealTypeLabel(mealType: MealType): string {
  const labels: Record<MealType, string> = {
    breakfast: copy.scan.mealTypes.breakfast,
    lunch: copy.scan.mealTypes.lunch,
    dinner: copy.scan.mealTypes.dinner,
    snack: copy.scan.mealTypes.snack,
    custom: copy.scan.mealTypes.custom,
  };

  return labels[mealType];
}

export function getMealTitle(meal: Meal): string {
  return meal.name || getMealTypeLabel(meal.meal_type);
}

export function getMealItemCountLabel(count: number): string {
  return `${count} поз.`;
}

export function getMealTimeLabel(loggedAt: string): string {
  return new Date(loggedAt).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getMealTotals(items: MealItem[]): MealNutritionTotals {
  return items.reduce(
    (totals, item) => ({
      calories: totals.calories + Number(item.calories || 0),
      protein: totals.protein + Number(item.protein || 0),
      fat: totals.fat + Number(item.fat || 0),
      carbs: totals.carbs + Number(item.carbs || 0),
    }),
    { calories: 0, protein: 0, fat: 0, carbs: 0 },
  );
}

export function getNutritionSummaryLabel(totals: MealNutritionTotals): string {
  return `${formatDecimal(totals.calories, 0)} ккал · Б ${formatDecimal(
    totals.protein,
    1,
  )} · Ж ${formatDecimal(totals.fat, 1)} · У ${formatDecimal(totals.carbs, 1)}`;
}

export function getToday(): string {
  return toDatetimeLocalValue(new Date()).slice(0, 10);
}

export function getDefaultLoggedAt(date: string): string {
  const now = new Date();
  const time = now.toTimeString().slice(0, 5);
  return `${date}T${time}`;
}

export function toIsoString(datetimeLocal: string): string {
  const parsedDate = new Date(datetimeLocal);
  return Number.isNaN(parsedDate.getTime()) ? new Date().toISOString() : parsedDate.toISOString();
}

export function toDatetimeLocalValue(date: Date): string {
  const timezoneOffsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - timezoneOffsetMs).toISOString().slice(0, 16);
}
