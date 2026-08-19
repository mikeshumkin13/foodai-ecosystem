import { apiRequest } from "./client";
import type { DiaryDay, Meal, MealPayload } from "./types";

export type MealFilters = {
  date?: string;
  date_from?: string;
  date_to?: string;
};

export const diaryApi = {
  listMeals(filters: MealFilters = {}) {
    return apiRequest<Meal[]>(`/api/v1/meals/${toQueryString(filters)}`);
  },
  day(date: string) {
    return apiRequest<DiaryDay>(`/api/v1/diary/day/?date=${encodeURIComponent(date)}`);
  },
  createMeal(payload: MealPayload) {
    return apiRequest<Meal>("/api/v1/meals/", {
      method: "POST",
      body: payload,
    });
  },
  updateMeal(mealId: string, payload: MealPayload) {
    return apiRequest<Meal>(`/api/v1/meals/${mealId}/`, {
      method: "PATCH",
      body: payload,
    });
  },
  deleteMeal(mealId: string) {
    return apiRequest<void>(`/api/v1/meals/${mealId}/`, {
      method: "DELETE",
    });
  },
};

function toQueryString(filters: MealFilters): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      searchParams.set(key, value);
    }
  }

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}
