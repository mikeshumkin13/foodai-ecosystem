"use client";

import { useEffect, useMemo, useState } from "react";

import { diaryApi } from "@/lib/api/diary";
import { getErrorMessage } from "@/lib/api/errors";
import { profileApi } from "@/lib/api/profile";
import type { DiaryDay, NutritionProfile } from "@/lib/api/types";

import { getToday } from "../diary/meal-utils";
import { getDashboardMetrics } from "./dashboard-metrics";
import { DashboardSummary } from "./dashboard-summary";

export function DashboardPanel() {
  const today = useMemo(() => getToday(), []);
  const [reloadKey, setReloadKey] = useState(0);
  const [diaryDay, setDiaryDay] = useState<DiaryDay | null>(null);
  const [nutritionProfile, setNutritionProfile] = useState<NutritionProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadDashboard() {
      setIsLoading(true);
      setError(null);

      try {
        const [diaryResult, profileResult] = await Promise.allSettled([
          diaryApi.day(today),
          profileApi.getCurrentNutritionProfile(),
        ]);

        if (!isActive) {
          return;
        }

        if (diaryResult.status === "fulfilled") {
          setDiaryDay(diaryResult.value);
        } else {
          setError(getErrorMessage(diaryResult.reason));
        }

        if (profileResult.status === "fulfilled") {
          setNutritionProfile(profileResult.value);
        } else {
          setNutritionProfile(null);
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => {
      isActive = false;
    };
  }, [today, reloadKey]);

  return (
    <DashboardSummary
      diaryDay={diaryDay}
      error={error}
      isLoading={isLoading}
      metrics={getDashboardMetrics(diaryDay, nutritionProfile)}
      onRefresh={() => setReloadKey((currentKey) => currentKey + 1)}
    />
  );
}
