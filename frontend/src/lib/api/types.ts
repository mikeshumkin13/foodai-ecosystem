export type LocaleCode = "ru" | "en";

export type ApiCodeResponse = {
  code: string;
};

export type UserProfile = {
  id: string;
  user_id: string;
  display_name: string;
  preferred_language: LocaleCode;
  created_at: string;
  updated_at: string;
};

export type UserSummary = {
  id: string;
  email: string;
  is_active: boolean;
  roles: string[];
  profile: UserProfile;
  created_at: string;
  updated_at: string;
};

export type AuthUserResponse = {
  code: string;
  user: UserSummary;
};

export type NutritionProfile = {
  id: string;
  user_id: string;
  goal: string;
  height_cm: string | null;
  mass_kg: string | null;
  age_category: string;
  activity_level: string;
  preferred_units: string;
  dietary_preferences: string[];
  consent_version: string;
  consent_granted_at: string | null;
  consent_revoked_at: string | null;
  created_at: string;
  updated_at: string;
};

export type NutrientSnapshot = Record<
  string,
  {
    amount: string;
    unit: string;
  }
>;

export type MealItem = {
  id: string;
  food_id: string;
  food_name_snapshot: string;
  food_source_reference_snapshot: string;
  mass_g: string;
  calories: string;
  protein: string;
  fat: string;
  carbs: string;
  micronutrient_snapshot: NutrientSnapshot;
  nutrient_snapshot: NutrientSnapshot;
  source: string;
  confidence: string | null;
  manually_corrected: boolean;
  created_at: string;
  updated_at: string;
};

export type Meal = {
  id: string;
  user_id: string;
  meal_type: "breakfast" | "lunch" | "dinner" | "snack" | "custom";
  logged_at: string;
  name: string;
  items: MealItem[];
  created_at: string;
  updated_at: string;
};

export type DiaryDay = {
  date: string;
  totals: {
    calories: string;
    protein: string;
    fat: string;
    carbs: string;
  };
  micronutrient_totals: NutrientSnapshot;
  meals: Meal[];
};

export type FoodSearchItem = {
  id: string;
  name: string;
  name_ru: string;
  name_en: string;
  category: {
    id: string;
    name: string;
  } | null;
  verified: boolean;
};

export type FoodScanStatus =
  | "uploaded"
  | "processing"
  | "needs_confirmation"
  | "confirmed"
  | "failed";

export type FoodScanUploadResponse = {
  scan_id: string;
  status: FoodScanStatus;
};

export type PortionEstimate = {
  estimated_volume: string;
  estimated_mass: string;
  confidence: string;
  min_estimate: string;
  max_estimate: string;
  method: string;
};

export type FoodScanDetectedItem = {
  id: string;
  label: string;
  confidence: string;
  food_id: string | null;
  food: {
    id: string;
    name: string;
    name_ru: string;
    name_en: string;
  } | null;
  mass_g: string;
  manual_mass_g: string | null;
  portion_estimate: PortionEstimate | null;
  calories: string;
  protein: string;
  fat: string;
  carbs: string;
  nutrient_snapshot: NutrientSnapshot;
  micronutrient_snapshot: NutrientSnapshot;
  source: string;
  is_removed: boolean;
  manually_corrected: boolean;
  created_at: string;
  updated_at: string;
};

export type FoodScanResult = {
  id: string;
  user_id: string;
  status: FoodScanStatus;
  failure_code: string;
  confirmed_meal_id: string | null;
  image_format: string;
  content_type: string;
  uploaded_byte_size: number;
  stored_byte_size: number;
  width: number;
  height: number;
  exif_stripped: boolean;
  created_at: string;
  updated_at: string;
  detected_items: FoodScanDetectedItem[];
};

export type FoodScanConfirmResponse = {
  food_scan: FoodScanResult;
  meal: Meal;
};
