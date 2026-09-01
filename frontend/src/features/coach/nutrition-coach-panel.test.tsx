// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { aiCoachApi } from "@/lib/api/ai-coach";
import type { AICoachResponse, AICoachSettings } from "@/lib/api/types";

import { NutritionCoachPanel } from "./nutrition-coach-panel";

vi.mock("@/lib/api/ai-coach", () => ({
  aiCoachApi: {
    getSettings: vi.fn(),
    updateHistoryConsent: vi.fn(),
    ask: vi.fn(),
  },
}));

describe("NutritionCoachPanel", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.mocked(aiCoachApi.getSettings).mockReset();
    vi.mocked(aiCoachApi.updateHistoryConsent).mockReset();
    vi.mocked(aiCoachApi.ask).mockReset();
    vi.mocked(aiCoachApi.getSettings).mockResolvedValue(settings);
  });

  it("renders a structured nutrition response without storing it by default", async () => {
    vi.mocked(aiCoachApi.ask).mockResolvedValue(successResponse);
    render(<NutritionCoachPanel />);

    const message = await screen.findByLabelText("Ваш вопрос");
    fireEvent.change(message, { target: { value: "Как добрать белок?" } });
    fireEvent.submit(screen.getByRole("button", { name: "Получить разбор" }).closest("form")!);

    await waitFor(() => {
      expect(aiCoachApi.ask).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "Как добрать белок?",
          store_response: false,
        }),
      );
    });
    expect(await screen.findByRole("heading", { name: "Разбор питания" })).toBeTruthy();
    expect(screen.getByText("Добавьте источник белка к ужину.")).toBeTruthy();
    expect(screen.getByText("Ответ не сохранён в истории.")).toBeTruthy();
  });

  it("shows a safety response as a blocked result", async () => {
    vi.mocked(aiCoachApi.ask).mockResolvedValue({
      ...successResponse,
      code: "ai_coach_safety_blocked",
      answer: "Я не могу помочь с опасной диетой.",
      suggestions: [],
      nutrition_notes: [],
      warnings: ["ai_coach_safety_boundary"],
      safety: {
        blocked: true,
        code: "dangerous_diet",
        categories: ["extreme_diet"],
        reason: "unsafe_request",
      },
    });
    render(<NutritionCoachPanel />);

    fireEvent.change(await screen.findByLabelText("Ваш вопрос"), {
      target: { value: "Опасный запрос" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Получить разбор" }).closest("form")!);

    expect(
      await screen.findByRole("heading", { name: "Запрос требует другого вида помощи" }),
    ).toBeTruthy();
    expect(screen.getByText("Я не могу помочь с опасной диетой.")).toBeTruthy();
  });
});

const settings: AICoachSettings = {
  id: "settings-1",
  chat_history_enabled: false,
  chat_history_consent_version: "ai_coach_history_mvp_v1",
  chat_history_consent_granted_at: null,
  chat_history_consent_revoked_at: null,
  created_at: "2026-08-26T10:00:00Z",
  updated_at: "2026-08-26T10:00:00Z",
};

const successResponse: AICoachResponse = {
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
};
