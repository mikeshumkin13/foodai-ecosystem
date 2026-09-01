import { expect, test } from "@playwright/test";
import type { Page, Route } from "@playwright/test";
import type { NutritionProfile } from "../src/lib/api/types";

const user = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "mvp@example.com",
  is_active: true,
  roles: ["user"],
  profile: {
    id: "22222222-2222-4222-8222-222222222222",
    user_id: "11111111-1111-4111-8111-111111111111",
    display_name: "MVP User",
    preferred_language: "ru",
    created_at: "2026-08-26T10:00:00Z",
    updated_at: "2026-08-26T10:00:00Z",
  },
  created_at: "2026-08-26T10:00:00Z",
  updated_at: "2026-08-26T10:00:00Z",
};

const nutritionProfile: NutritionProfile = {
  id: "33333333-3333-4333-8333-333333333333",
  user_id: user.id,
  goal: "maintain_weight",
  height_cm: null,
  mass_kg: null,
  age_category: "prefer_not_to_say",
  activity_level: "moderate",
  preferred_units: "metric",
  dietary_preferences: [],
  consent_version: "nutrition_profile_mvp_v1",
  consent_granted_at: null,
  consent_revoked_at: null,
  created_at: "2026-08-26T10:00:00Z",
  updated_at: "2026-08-26T10:00:00Z",
};

test("registration, email verification and login open the protected dashboard", async ({ page }) => {
  let authenticated = false;
  await mockApi(page, async (route, path, method) => {
    if (path === "/api/v1/auth/me/") {
      return authenticated
        ? json(route, user)
        : json(route, { detail: "Authentication credentials were not provided." }, 403);
    }
    if (path === "/api/v1/auth/register/" && method === "POST") {
      return json(route, { code: "registration_created", user: { ...user, is_active: false } }, 201);
    }
    if (path === "/api/v1/auth/email/verify/" && method === "POST") {
      return json(route, { code: "email_verified" });
    }
    if (path === "/api/v1/auth/login/" && method === "POST") {
      authenticated = true;
      return json(route, { code: "login_success", user });
    }
    return commonAuthenticatedResponse(route, path);
  });

  await page.goto("/register");
  await page.getByLabel("Email").fill("mvp@example.com");
  await page.getByLabel("Пароль").fill("correct-password");
  await page.getByRole("button", { name: "Создать аккаунт" }).click();
  await expect(page.getByRole("heading", { name: "Подтвердите email" })).toBeVisible();

  await page.goto("/auth/email/verify?token_id=token-id&token=token-value");
  await expect(page.getByRole("heading", { name: "Email подтверждён" })).toBeVisible();
  await page.getByRole("link", { name: "Войти" }).click();
  await page.getByLabel("Email").fill("mvp@example.com");
  await page.getByLabel("Пароль").fill("correct-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Обзор дня" })).toBeVisible();
});

test("profile settings feed a structured AI nutrition summary", async ({ page }) => {
  let savedProfile = nutritionProfile;
  await mockApi(page, async (route, path, method) => {
    if (path === "/api/v1/accounts/nutrition-profiles/me/") {
      return json(route, savedProfile);
    }
    if (path === `/api/v1/accounts/nutrition-profiles/${nutritionProfile.id}/` && method === "PATCH") {
      savedProfile = {
        ...savedProfile,
        goal: "lose_weight",
        height_cm: 181,
        mass_kg: "82.40",
        consent_granted_at: "2026-08-26T10:30:00Z",
      };
      return json(route, savedProfile);
    }
    if (path === "/api/v1/ai/coach/settings/") {
      return json(route, aiSettings);
    }
    if (path === "/api/v1/ai/coach/ask/" && method === "POST") {
      return json(route, {
        code: "ai_coach_response",
        schema_version: "ai_nutrition_coach_response_v1",
        context_date: "2026-08-26",
        answer: "Белок можно распределить между приёмами пищи.",
        suggestions: ["Добавьте источник белка к ужину."],
        nutrition_notes: [{ code: "protein", message: "Оцените белок за весь день." }],
        warnings: [],
        safety: { blocked: false, code: "passed", categories: [], reason: "" },
        provider: "mock",
        stored: false,
      });
    }
    return commonAuthenticatedResponse(route, path);
  });

  await page.goto("/profile");
  await page.getByLabel("Цель").selectOption("lose_weight");
  await page.getByLabel("Рост, см").fill("181");
  await page.getByLabel("Масса, кг").fill("82.40");
  await page.getByLabel("Я согласен сохранить эти данные в nutrition profile.").check();
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page.getByText("Профиль питания сохранён.")).toBeVisible();

  await page.goto("/coach");
  await page.getByLabel("Ваш вопрос").fill("Как добрать белок?");
  await page.getByRole("button", { name: "Получить разбор" }).click();
  await expect(page.getByRole("heading", { name: "Разбор питания" })).toBeVisible();
  await expect(page.getByText("Добавьте источник белка к ужину.")).toBeVisible();
  await expect(page.getByText("Ответ не сохранён в истории.")).toBeVisible();
});

test("confirmed food scan appears in the diary", async ({ page }) => {
  let confirmed = false;
  await mockApi(page, async (route, path, method) => {
    if (path === "/api/v1/food-scans/" && method === "POST") {
      return json(route, { scan_id: "scan-1", status: "processing" }, 201);
    }
    if (path === "/api/v1/food-scans/scan-1/results/") {
      return json(route, scanResult);
    }
    if (path === "/api/v1/food-scans/scan-1/confirm/" && method === "POST") {
      confirmed = true;
      return json(route, {
        food_scan: { ...scanResult, status: "confirmed", confirmed_meal_id: meal.id },
        meal,
      });
    }
    if (path === "/api/v1/diary/day/") {
      return json(route, diaryDay(confirmed ? [meal] : []));
    }
    return commonAuthenticatedResponse(route, path);
  });

  await page.goto("/scan");
  await page.getByLabel("Фотография блюда").setInputFiles({
    name: "meal.png",
    mimeType: "image/png",
    buffer: Buffer.from("safe-e2e-image"),
  });
  await page.getByRole("button", { name: "Загрузить фото" }).click();
  await expect(page.getByRole("heading", { name: "Распознанные продукты" })).toBeVisible();
  await expect(page.getByText("≈ 180 г")).toBeVisible();
  await page.getByRole("button", { name: "Подтвердить и открыть дневник" }).click();
  await expect(page.getByRole("heading", { name: "Дневник питания" })).toBeVisible();
  await expect(page.getByText("Рис")).toBeVisible();
});

async function mockApi(
  page: Page,
  handler: (route: Route, path: string, method: string) => Promise<void>,
) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/v1/auth/csrf/") {
      return json(route, { code: "csrf_cookie_set", csrf_token: "e2e-csrf-token" });
    }
    await handler(route, url.pathname, request.method());
  });
}

async function commonAuthenticatedResponse(route: Route, path: string) {
  if (path === "/api/v1/auth/me/") {
    return json(route, user);
  }
  if (path === "/api/v1/accounts/nutrition-profiles/me/") {
    return json(route, { ...nutritionProfile, consent_granted_at: "2026-08-26T10:30:00Z" });
  }
  if (path === "/api/v1/diary/day/") {
    return json(route, diaryDay([]));
  }
  return json(route, { code: "not_mocked" }, 404);
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

const aiSettings = {
  id: "settings-1",
  chat_history_enabled: false,
  chat_history_consent_version: "ai_coach_history_mvp_v1",
  chat_history_consent_granted_at: null,
  chat_history_consent_revoked_at: null,
  created_at: "2026-08-26T10:00:00Z",
  updated_at: "2026-08-26T10:00:00Z",
};

const detectedItem = {
  id: "item-1",
  label: "rice",
  confidence: "0.92",
  food_id: "food-1",
  food: { id: "food-1", name: "Rice", name_ru: "Рис", name_en: "Rice" },
  mass_g: "180.00",
  manual_mass_g: null,
  portion_estimate: {
    estimated_volume: "210.00",
    estimated_mass: "180.00",
    confidence: "0.62",
    min_estimate: "155.00",
    max_estimate: "205.00",
    method: "density_table",
  },
  calories: "234.00",
  protein: "4.90",
  fat: "0.50",
  carbs: "50.80",
  nutrient_snapshot: {},
  micronutrient_snapshot: {},
  source: "vision",
  is_removed: false,
  manually_corrected: false,
  created_at: "2026-08-26T10:00:00Z",
  updated_at: "2026-08-26T10:00:00Z",
};

const scanResult = {
  id: "scan-1",
  user_id: user.id,
  status: "needs_confirmation",
  failure_code: "",
  confirmed_meal_id: null,
  image_format: "PNG",
  content_type: "image/png",
  uploaded_byte_size: 128,
  stored_byte_size: 96,
  width: 640,
  height: 480,
  exif_stripped: true,
  created_at: "2026-08-26T10:00:00Z",
  updated_at: "2026-08-26T10:00:00Z",
  detected_items: [detectedItem],
};

const meal = {
  id: "meal-1",
  user_id: user.id,
  meal_type: "lunch",
  logged_at: "2026-08-26T12:30:00Z",
  name: "Обед",
  items: [
    {
      id: "meal-item-1",
      food_id: "food-1",
      food_name_snapshot: "Рис",
      food_source_reference_snapshot: "demo",
      mass_g: "180.00",
      calories: "234.00",
      protein: "4.90",
      fat: "0.50",
      carbs: "50.80",
      micronutrient_snapshot: {},
      nutrient_snapshot: {},
      source: "vision",
      confidence: "0.92",
      manually_corrected: false,
      created_at: "2026-08-26T10:00:00Z",
      updated_at: "2026-08-26T10:00:00Z",
    },
  ],
  created_at: "2026-08-26T10:00:00Z",
  updated_at: "2026-08-26T10:00:00Z",
};

function diaryDay(meals: unknown[]) {
  return {
    date: "2026-08-26",
    totals: meals.length
      ? { calories: "234.00", protein: "4.90", fat: "0.50", carbs: "50.80" }
      : { calories: "0", protein: "0", fat: "0", carbs: "0" },
    micronutrient_totals: {},
    meals,
  };
}
