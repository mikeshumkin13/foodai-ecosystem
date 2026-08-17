import { apiRequest } from "./client";
import type { DiaryDay, Meal } from "./types";

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
