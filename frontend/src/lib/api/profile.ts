import { apiRequest } from "./client";
import type { NutritionProfile } from "./types";

export type NutritionProfileUpdate = Partial<
  Pick<
    NutritionProfile,
    "goal" | "height_cm" | "mass_kg" | "age_category" | "activity_level" | "preferred_units"
  >
> & {
  dietary_preferences?: string[];
  consent_accepted?: boolean;
};

export const profileApi = {
  getCurrentNutritionProfile() {
    return apiRequest<NutritionProfile>("/api/v1/accounts/nutrition-profiles/me/");
  },
  getNutritionProfile(id: string) {
    return apiRequest<NutritionProfile>(`/api/v1/accounts/nutrition-profiles/${id}/`);
  },
  updateNutritionProfile(id: string, payload: NutritionProfileUpdate) {
    return apiRequest<NutritionProfile>(`/api/v1/accounts/nutrition-profiles/${id}/`, {
      method: "PATCH",
      body: payload,
    });
  },
};
