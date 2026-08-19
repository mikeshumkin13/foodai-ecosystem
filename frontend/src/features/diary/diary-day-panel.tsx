"use client";

import {
  CalendarDays,
  Camera,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  Utensils,
} from "lucide-react";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { TextField } from "@/components/ui/text-field";
import { diaryApi } from "@/lib/api/diary";
import { getErrorMessage } from "@/lib/api/errors";
import type { DiaryDay, Meal, MealPayload } from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

import { formatDecimal, formatGrams } from "../scan/scan-format";
import { MealEditor } from "./meal-editor";
import { getMealItemCountLabel, getMealTimeLabel, getMealTitle, getToday } from "./meal-utils";

const copy = messages.ru;

export function DiaryDayPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialDate = useMemo(() => searchParams.get("date") ?? getToday(), [searchParams]);
  const [date, setDate] = useState(initialDate);
  const [reloadKey, setReloadKey] = useState(0);
  const [diaryDay, setDiaryDay] = useState<DiaryDay | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingMeal, setEditingMeal] = useState<Meal | null>(null);
  const [isSavingMeal, setIsSavingMeal] = useState(false);
  const [deletingMealId, setDeletingMealId] = useState<string | null>(null);
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
    setIsEditorOpen(false);
    setEditingMeal(null);
    router.replace(`/diary?date=${encodeURIComponent(nextDate)}`);
  }

  function handleAddMeal() {
    setEditingMeal(null);
    setIsEditorOpen(true);
  }

  function handleEditMeal(meal: Meal) {
    setEditingMeal(meal);
    setIsEditorOpen(true);
  }

  async function handleSaveMeal(payload: MealPayload) {
    setIsSavingMeal(true);
    setError(null);
    try {
      if (editingMeal) {
        await diaryApi.updateMeal(editingMeal.id, payload);
      } else {
        await diaryApi.createMeal(payload);
      }
      setIsEditorOpen(false);
      setEditingMeal(null);
      setReloadKey((currentKey) => currentKey + 1);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSavingMeal(false);
    }
  }

  async function handleDeleteMeal(meal: Meal) {
    if (!window.confirm(copy.diary.deleteConfirm)) {
      return;
    }

    setDeletingMealId(meal.id);
    setError(null);
    try {
      await diaryApi.deleteMeal(meal.id);
      if (editingMeal?.id === meal.id) {
        setIsEditorOpen(false);
        setEditingMeal(null);
      }
      setReloadKey((currentKey) => currentKey + 1);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setDeletingMealId(null);
    }
  }

  return (
    <section className="diary-day-panel" aria-label={copy.diary.title}>
      <div className="toolbar">
        <TextField label={copy.diary.date} name="date" onChange={handleDateChange} type="date" value={date} />
        <div className="toolbar__actions">
          <Button icon={<Plus aria-hidden="true" size={18} />} onClick={handleAddMeal}>
            {copy.diary.addManualMeal}
          </Button>
          <Link className="button button--secondary" href="/scan">
            <Camera aria-hidden="true" size={18} />
            <span>{copy.diary.addViaScan}</span>
          </Link>
          <Button
            disabled={isLoading}
            icon={<RefreshCw aria-hidden="true" size={18} />}
            onClick={() => setReloadKey((currentKey) => currentKey + 1)}
            variant="secondary"
          >
            {copy.common.refresh}
          </Button>
        </div>
      </div>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading && !diaryDay ? <LoadingState label={copy.common.loading} /> : null}

      {isEditorOpen ? (
        <MealEditor
          date={date}
          isSaving={isSavingMeal}
          meal={editingMeal}
          onCancel={() => {
            setIsEditorOpen(false);
            setEditingMeal(null);
          }}
          onSubmit={(payload) => void handleSaveMeal(payload)}
        />
      ) : null}

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
                <MealCard
                  key={meal.id}
                  isDeleting={deletingMealId === meal.id}
                  meal={meal}
                  onDelete={() => void handleDeleteMeal(meal)}
                  onEdit={() => handleEditMeal(meal)}
                />
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

function MealCard({
  meal,
  isDeleting,
  onEdit,
  onDelete,
}: {
  meal: Meal;
  isDeleting: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card className="meal-card">
      <div className="meal-card__header">
        <div>
          <p>{getMealTimeLabel(meal.logged_at)}</p>
          <h2>{getMealTitle(meal)}</h2>
        </div>
        <div className="meal-card__actions">
          <span>{getMealItemCountLabel(meal.items.length)}</span>
          <Button icon={<Pencil aria-hidden="true" size={17} />} onClick={onEdit} variant="secondary">
            {copy.diary.editMeal}
          </Button>
          <Button
            disabled={isDeleting}
            icon={<Trash2 aria-hidden="true" size={17} />}
            onClick={onDelete}
            variant="ghost"
          >
            {isDeleting ? copy.common.saving : copy.diary.deleteMeal}
          </Button>
        </div>
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
