import { apiRequest } from "./client";
import type { FoodSearchItem } from "./types";

export const foodsApi = {
  search(query: string) {
    return apiRequest<FoodSearchItem[]>(
      `/api/v1/foods/search/?q=${encodeURIComponent(query.trim())}`,
    );
  },
};
