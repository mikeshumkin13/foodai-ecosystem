"use client";

import { CalendarDays, RefreshCw, Utensils } from "lucide-react";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { TextField } from "@/components/ui/text-field";
import { diaryApi } from "@/lib/api/diary";
import { getErrorMessage } from "@/lib/api/errors";
import type { DiaryDay, Meal } from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

import { formatDecimal, formatGrams } from "../scan/scan-format";

const copy = messages.ru;

export function DiaryDayPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialDate = useMemo(() => searchParams.get("date") ?? getToday(), [searchParams]);
  const [date, setDate] = useState(initialDate);
  const [reloadKey, setReloadKey] = useState(0);
  const [diaryDay, setDiaryDay] = useState<DiaryDay | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDate(initialDate);
  }, [initialDate]);

  useEffect(() => {
    let isActive = true;

    async function loadDiaryDay() {
      setIsLoading(true);
      setError(null);
      try {
        const response = await diaryApi.day(date);
        if (isActive) {
          setDiaryDay(response);
        }
      } catch (requestError) {
        if (isActive) {
          setError(getErrorMessage(requestError));
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadDiaryDay();

    return () => {
      isActive = false;
    };
  }, [date, reloadKey]);

  function handleDateChange(event: ChangeEvent<HTMLInputElement>) {
    const nextDate = event.target.value;
    setDate(nextDate);
    router.replace(`/diary?date=${encodeURIComponent(nextDate)}`);
  }

  return (
    <section className="diary-day-panel" aria-label={copy.diary.title}>
      <div className="toolbar">
        <TextField label={copy.diary.date} name="date" onChange={handleDateChange} type="date" value={date} />
        <Button
          disabled={isLoading}
          icon={<RefreshCw aria-hidden="true" size={18} />}
          onClick={() => setReloadKey((currentKey) => currentKey + 1)}
          variant="secondary"
        >
          {copy.common.refresh}
        </Button>
      </div>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading && !diaryDay ? <LoadingState label={copy.common.loading} /> : null}

      {diaryDay ? (
        <>
          <div className="metrics-grid">
            <DiaryMetric label={copy.dashboard.calories} unit="ккал" value={diaryDay.totals.calories} />
            <DiaryMetric label={copy.dashboard.protein} unit="г" value={diaryDay.totals.protein} />
            <DiaryMetric label={copy.dashboard.fat} unit="г" value={diaryDay.totals.fat} />
            <DiaryMetric label={copy.dashboard.carbs} unit="г" value={diaryDay.totals.carbs} />
          </div>

          {diaryDay.meals.length > 0 ? (
            <div className="meal-list">
              {diaryDay.meals.map((meal) => (
                <MealCard key={meal.id} meal={meal} />
              ))}
            </div>
          ) : (
            <Card className="panel panel--wide">
              <div className="panel__media-icon">
                <CalendarDays aria-hidden="true" size={28} strokeWidth={1.8} />
              </div>
              <EmptyState title={copy.diary.emptyTitle} description={copy.diary.emptyDescription} />
            </Card>
          )}
        </>
      ) : null}
    </section>
  );
}

function DiaryMetric({ label, unit, value }: { label: string; unit: string; value: string }) {
  return (
    <Card className="metric-card">
      <div className="metric-card__icon">
        <Utensils aria-hidden="true" size={22} strokeWidth={1.8} />
      </div>
      <div>
        <span>{label}</span>
        <strong>
          {formatDecimal(value, unit === "ккал" ? 0 : 1)}
          <small>{unit}</small>
        </strong>
      </div>
    </Card>
  );
}

function MealCard({ meal }: { meal: Meal }) {
  const mealTitle = meal.name || getMealTypeLabel(meal.meal_type);

  return (
    <Card className="meal-card">
      <div className="meal-card__header">
        <div>
          <p>{new Date(meal.logged_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}</p>
          <h2>{mealTitle}</h2>
        </div>
        <span>{meal.items.length} поз.</span>
      </div>

      <div className="meal-card__items">
        {meal.items.map((item) => (
          <div key={item.id} className="meal-card__item">
            <div>
              <strong>{item.food_name_snapshot}</strong>
              <small>{formatGrams(item.mass_g)}</small>
            </div>
            <div className="meal-card__nutrients">
              <span>{formatDecimal(item.calories, 0)} ккал</span>
              <span>Б {formatDecimal(item.protein, 1)}</span>
              <span>Ж {formatDecimal(item.fat, 1)}</span>
              <span>У {formatDecimal(item.carbs, 1)}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function getMealTypeLabel(mealType: Meal["meal_type"]): string {
  const labels: Record<Meal["meal_type"], string> = {
    breakfast: copy.scan.mealTypes.breakfast,
    lunch: copy.scan.mealTypes.lunch,
    dinner: copy.scan.mealTypes.dinner,
    snack: copy.scan.mealTypes.snack,
    custom: copy.scan.mealTypes.custom,
  };

  return labels[mealType];
}

function getToday(): string {
  return new Date().toISOString().slice(0, 10);
}
