import { ArrowRight, Plus, Utensils } from "lucide-react";
import type { ChangeEvent, FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import type { FoodScanDetectedItem, FoodSearchItem } from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

import { formatDecimal, getFoodSearchDisplayName, getScanTotals } from "./scan-format";

const copy = messages.ru;

type ScanReviewSummaryProps = {
  items: FoodScanDetectedItem[];
  mealType: string;
  loggedAt: string;
  addQuery: string;
  addMass: string;
  addOptions: FoodSearchItem[];
  selectedAddFoodId: string;
  isSearchingAddFood: boolean;
  isAddingItem: boolean;
  isConfirming: boolean;
  canConfirm: boolean;
  onMealTypeChange: (value: string) => void;
  onLoggedAtChange: (value: string) => void;
  onAddQueryChange: (value: string) => void;
  onAddMassChange: (value: string) => void;
  onSearchAddFood: () => void;
  onSelectedAddFoodChange: (value: string) => void;
  onAddItem: () => void;
  onConfirm: () => void;
};

const mealTypeOptions = [
  { value: "breakfast", label: copy.scan.mealTypes.breakfast },
  { value: "lunch", label: copy.scan.mealTypes.lunch },
  { value: "dinner", label: copy.scan.mealTypes.dinner },
  { value: "snack", label: copy.scan.mealTypes.snack },
  { value: "custom", label: copy.scan.mealTypes.custom },
];

export function ScanReviewSummary({
  items,
  mealType,
  loggedAt,
  addQuery,
  addMass,
  addOptions,
  selectedAddFoodId,
  isSearchingAddFood,
  isAddingItem,
  isConfirming,
  canConfirm,
  onMealTypeChange,
  onLoggedAtChange,
  onAddQueryChange,
  onAddMassChange,
  onSearchAddFood,
  onSelectedAddFoodChange,
  onAddItem,
  onConfirm,
}: ScanReviewSummaryProps) {
  const totals = getScanTotals(items);

  function handleMealTypeChange(event: ChangeEvent<HTMLSelectElement>) {
    onMealTypeChange(event.target.value);
  }

  function handleLoggedAtChange(event: ChangeEvent<HTMLInputElement>) {
    onLoggedAtChange(event.target.value);
  }

  function handleAddQueryChange(event: ChangeEvent<HTMLInputElement>) {
    onAddQueryChange(event.target.value);
  }

  function handleAddMassChange(event: ChangeEvent<HTMLInputElement>) {
    onAddMassChange(event.target.value);
  }

  function handleAddSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onAddItem();
  }

  return (
    <aside className="scan-review-summary">
      <div className="scan-review-summary__header">
        <Utensils aria-hidden="true" size={22} strokeWidth={1.8} />
        <div>
          <h2>{copy.scan.summaryTitle}</h2>
          <p>{copy.scan.summaryDescription}</p>
        </div>
      </div>

      <div className="nutrition-row nutrition-row--summary" aria-label={copy.scan.summaryNutritionLabel}>
        <span>
          <strong>{formatDecimal(totals.calories, 0)}</strong>
          <small>{copy.scan.caloriesUnit}</small>
        </span>
        <span>
          <strong>{formatDecimal(totals.protein, 1)}</strong>
          <small>{copy.scan.protein}</small>
        </span>
        <span>
          <strong>{formatDecimal(totals.fat, 1)}</strong>
          <small>{copy.scan.fat}</small>
        </span>
        <span>
          <strong>{formatDecimal(totals.carbs, 1)}</strong>
          <small>{copy.scan.carbs}</small>
        </span>
      </div>

      <form className="add-food-form" onSubmit={handleAddSubmit}>
        <h3>{copy.scan.addMissingTitle}</h3>
        <div className="correction-grid__row">
          <TextField
            label={copy.scan.addFoodSearch}
            name="add-food-query"
            onChange={handleAddQueryChange}
            placeholder={copy.scan.addFoodPlaceholder}
            type="search"
            value={addQuery}
          />
          <Button
            disabled={isSearchingAddFood || addQuery.trim().length < 2}
            icon={<Plus aria-hidden="true" size={18} />}
            onClick={onSearchAddFood}
            variant="secondary"
          >
            {isSearchingAddFood ? copy.common.searching : copy.common.search}
          </Button>
        </div>

        <SelectField
          label={copy.scan.addFoodSelect}
          name="add-food-id"
          onChange={(event) => onSelectedAddFoodChange(event.target.value)}
          options={[
            { value: "", label: copy.scan.chooseFood },
            ...addOptions.map((food) => ({
              value: food.id,
              label: getFoodSearchDisplayName(food),
            })),
          ]}
          value={selectedAddFoodId}
        />

        <TextField
          label={copy.scan.addMass}
          min="1"
          name="add-food-mass"
          onChange={handleAddMassChange}
          step="1"
          type="number"
          value={addMass}
        />

        <Button
          disabled={isAddingItem || !selectedAddFoodId || !addMass}
          icon={<Plus aria-hidden="true" size={18} />}
          type="submit"
          variant="secondary"
        >
          {isAddingItem ? copy.common.adding : copy.common.add}
        </Button>
      </form>

      <div className="confirm-box">
        <SelectField
          label={copy.scan.mealType}
          name="meal-type"
          onChange={handleMealTypeChange}
          options={mealTypeOptions}
          value={mealType}
        />
        <TextField
          label={copy.scan.loggedAt}
          name="logged-at"
          onChange={handleLoggedAtChange}
          type="datetime-local"
          value={loggedAt}
        />
        <Button
          disabled={!canConfirm || isConfirming}
          icon={<ArrowRight aria-hidden="true" size={18} />}
          onClick={onConfirm}
        >
          {isConfirming ? copy.common.saving : copy.scan.confirmAction}
        </Button>
      </div>
    </aside>
  );
}
