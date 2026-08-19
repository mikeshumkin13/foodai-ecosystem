"use client";

import { Check, Plus, Search, Trash2, X } from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { foodsApi } from "@/lib/api/foods";
import type { FoodSearchItem, Meal, MealPayload, MealType } from "@/lib/api/types";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";

import { formatGrams, getFoodSearchDisplayName } from "../scan/scan-format";
import { getDefaultLoggedAt, getMealTypeLabel, toDatetimeLocalValue, toIsoString } from "./meal-utils";

const copy = messages.ru;

type DraftMealItem = {
  draftId: string;
  foodId: string;
  foodName: string;
  massG: string;
};

type MealEditorProps = {
  date: string;
  meal: Meal | null;
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (payload: MealPayload) => void;
};

const mealTypeOptions: Array<{ value: MealType; label: string }> = [
  { value: "breakfast", label: getMealTypeLabel("breakfast") },
  { value: "lunch", label: getMealTypeLabel("lunch") },
  { value: "dinner", label: getMealTypeLabel("dinner") },
  { value: "snack", label: getMealTypeLabel("snack") },
  { value: "custom", label: getMealTypeLabel("custom") },
];

export function MealEditor({ date, meal, isSaving, onCancel, onSubmit }: MealEditorProps) {
  const [mealType, setMealType] = useState<MealType>(meal?.meal_type ?? "breakfast");
  const [loggedAt, setLoggedAt] = useState(getInitialLoggedAt(date, meal));
  const [name, setName] = useState(meal?.name ?? "");
  const [draftItems, setDraftItems] = useState<DraftMealItem[]>(() => makeDraftItems(meal));
  const [foodQuery, setFoodQuery] = useState("");
  const [foodOptions, setFoodOptions] = useState<FoodSearchItem[]>([]);
  const [selectedFoodId, setSelectedFoodId] = useState("");
  const [massG, setMassG] = useState("100");
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedFood = useMemo(
    () => foodOptions.find((food) => food.id === selectedFoodId) ?? null,
    [foodOptions, selectedFoodId],
  );

  useEffect(() => {
    setMealType(meal?.meal_type ?? "breakfast");
    setLoggedAt(getInitialLoggedAt(date, meal));
    setName(meal?.name ?? "");
    setDraftItems(makeDraftItems(meal));
    setFoodQuery("");
    setFoodOptions([]);
    setSelectedFoodId("");
    setMassG("100");
    setError(null);
  }, [date, meal]);

  async function handleFoodSearch() {
    const query = foodQuery.trim();
    if (query.length < 2) {
      return;
    }

    setIsSearching(true);
    setError(null);
    try {
      const results = await foodsApi.search(query);
      setFoodOptions(results);
      setSelectedFoodId(results[0]?.id ?? "");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSearching(false);
    }
  }

  function handleAddItem() {
    if (!selectedFood || !massG) {
      return;
    }

    setDraftItems((currentItems) => [
      ...currentItems,
      {
        draftId: makeDraftId(),
        foodId: selectedFood.id,
        foodName: getFoodSearchDisplayName(selectedFood),
        massG,
      },
    ]);
    setFoodQuery("");
    setFoodOptions([]);
    setSelectedFoodId("");
    setMassG("100");
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (draftItems.length === 0) {
      setError(copy.diary.noDraftItems);
      return;
    }

    setError(null);
    onSubmit({
      meal_type: mealType,
      logged_at: toIsoString(loggedAt),
      name: name.trim(),
      items: draftItems.map((item) => ({
        food_id: item.foodId,
        mass_g: item.massG,
        source: "manual",
        manually_corrected: true,
      })),
    });
  }

  return (
    <form className="meal-editor" onSubmit={handleSubmit}>
      <header className="meal-editor__header">
        <div>
          <h2>{meal ? copy.diary.editEntryTitle : copy.diary.manualEntryTitle}</h2>
          <p>{copy.diary.manualEntryDescription}</p>
        </div>
        <Button icon={<X aria-hidden="true" size={18} />} onClick={onCancel} variant="ghost">
          {copy.common.cancel}
        </Button>
      </header>

      <div className="form-grid">
        <SelectField
          label={copy.scan.mealType}
          name="manual-meal-type"
          onChange={(event) => setMealType(event.target.value as MealType)}
          options={mealTypeOptions}
          value={mealType}
        />
        <TextField
          label={copy.scan.loggedAt}
          name="manual-logged-at"
          onChange={(event) => setLoggedAt(event.target.value)}
          type="datetime-local"
          value={loggedAt}
        />
        <TextField
          label={copy.diary.mealName}
          name="manual-meal-name"
          onChange={(event) => setName(event.target.value)}
          placeholder={copy.diary.mealNamePlaceholder}
          value={name}
        />
      </div>

      <div className="manual-food-search">
        <div className="correction-grid__row">
          <TextField
            label={copy.diary.foodSearch}
            name="manual-food-query"
            onChange={(event) => setFoodQuery(event.target.value)}
            placeholder={copy.diary.foodPlaceholder}
            type="search"
            value={foodQuery}
          />
          <Button
            disabled={isSearching || foodQuery.trim().length < 2}
            icon={<Search aria-hidden="true" size={18} />}
            onClick={() => void handleFoodSearch()}
            variant="secondary"
          >
            {isSearching ? copy.common.searching : copy.common.search}
          </Button>
        </div>

        <div className="manual-food-search__row">
          <SelectField
            label={copy.diary.foodSelect}
            name="manual-food-id"
            onChange={(event) => setSelectedFoodId(event.target.value)}
            options={[
              { value: "", label: copy.diary.chooseFood },
              ...foodOptions.map((food) => ({
                value: food.id,
                label: getFoodSearchDisplayName(food),
              })),
            ]}
            value={selectedFoodId}
          />
          <TextField
            label={copy.diary.mass}
            min="1"
            name="manual-food-mass"
            onChange={(event) => setMassG(event.target.value)}
            step="1"
            type="number"
            value={massG}
          />
          <Button
            disabled={!selectedFood || !massG}
            icon={<Plus aria-hidden="true" size={18} />}
            onClick={handleAddItem}
            variant="secondary"
          >
            {copy.diary.addItem}
          </Button>
        </div>
      </div>

      <section className="draft-items" aria-label={copy.diary.items}>
        <h3>{copy.diary.items}</h3>
        {draftItems.length > 0 ? (
          draftItems.map((item) => (
            <div className="draft-item" key={item.draftId}>
              <strong>{item.foodName}</strong>
              <TextField
                aria-label={`${copy.diary.mass}: ${item.foodName}`}
                label={copy.diary.mass}
                min="1"
                name={`draft-mass-${item.draftId}`}
                onChange={(event) => updateDraftMass(item.draftId, event.target.value, setDraftItems)}
                step="1"
                type="number"
                value={item.massG}
              />
              <span>{formatGrams(item.massG)}</span>
              <Button
                icon={<Trash2 aria-hidden="true" size={18} />}
                onClick={() => removeDraftItem(item.draftId, setDraftItems)}
                variant="ghost"
              >
                {copy.common.remove}
              </Button>
            </div>
          ))
        ) : (
          <p className="muted-note">{copy.diary.noDraftItems}</p>
        )}
      </section>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <Button disabled={isSaving || draftItems.length === 0} icon={<Check aria-hidden="true" size={18} />} type="submit">
        {isSaving ? copy.common.saving : meal ? copy.diary.updateMeal : copy.diary.saveMeal}
      </Button>
    </form>
  );
}

function makeDraftItems(meal: Meal | null): DraftMealItem[] {
  return (
    meal?.items.map((item) => ({
      draftId: item.id,
      foodId: item.food_id,
      foodName: item.food_name_snapshot,
      massG: item.mass_g,
    })) ?? []
  );
}

function getInitialLoggedAt(date: string, meal: Meal | null): string {
  if (meal) {
    return toDatetimeLocalValue(new Date(meal.logged_at));
  }

  return getDefaultLoggedAt(date);
}

function updateDraftMass(
  draftId: string,
  massG: string,
  setDraftItems: (callback: (items: DraftMealItem[]) => DraftMealItem[]) => void,
) {
  setDraftItems((currentItems) =>
    currentItems.map((item) => (item.draftId === draftId ? { ...item, massG } : item)),
  );
}

function removeDraftItem(
  draftId: string,
  setDraftItems: (callback: (items: DraftMealItem[]) => DraftMealItem[]) => void,
) {
  setDraftItems((currentItems) => currentItems.filter((item) => item.draftId !== draftId));
}

function makeDraftId(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
