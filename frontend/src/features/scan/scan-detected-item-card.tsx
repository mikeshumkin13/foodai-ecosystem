import { Check, Search, Trash2 } from "lucide-react";
import type { ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import type { FoodScanDetectedItem, FoodSearchItem } from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

import {
  formatApproximateGrams,
  formatDecimal,
  formatGrams,
  formatPercent,
  getDetectedItemDisplayName,
  getFoodSearchDisplayName,
  getMassDraftValue,
  getPortionRangeLabel,
} from "./scan-format";

const copy = messages.ru;

type ScanDetectedItemCardProps = {
  item: FoodScanDetectedItem;
  massDraft: string;
  foodQuery: string;
  foodOptions: FoodSearchItem[];
  isSaving: boolean;
  isSearching: boolean;
  onMassDraftChange: (value: string) => void;
  onSaveMass: () => void;
  onFoodQueryChange: (value: string) => void;
  onFoodSearch: () => void;
  onSelectFood: (food: FoodSearchItem) => void;
  onRemove: () => void;
};

export function ScanDetectedItemCard({
  item,
  massDraft,
  foodQuery,
  foodOptions,
  isSaving,
  isSearching,
  onMassDraftChange,
  onSaveMass,
  onFoodQueryChange,
  onFoodSearch,
  onSelectFood,
  onRemove,
}: ScanDetectedItemCardProps) {
  const displayName = getDetectedItemDisplayName(item);
  const initialMass = item.portion_estimate?.estimated_mass ?? item.mass_g;
  const portionRangeLabel = getPortionRangeLabel(item);
  const activeMass = getMassDraftValue(item);

  function handleMassChange(event: ChangeEvent<HTMLInputElement>) {
    onMassDraftChange(event.target.value);
  }

  function handleFoodQueryChange(event: ChangeEvent<HTMLInputElement>) {
    onFoodQueryChange(event.target.value);
  }

  return (
    <article className="scan-item-card">
      <div className="scan-item-card__header">
        <div>
          <p className="scan-item-card__label">{item.label}</p>
          <h2>{displayName}</h2>
        </div>
        <div className="confidence-badge">
          <span>{formatPercent(item.confidence)}</span>
          <small>
            {Number(item.confidence) < 0.65
              ? copy.scan.confidenceVerify
              : copy.scan.confidenceLabel}
          </small>
        </div>
      </div>

      <div className="portion-box" aria-label={copy.scan.itemLabel}>
        <div>
          <span>{copy.scan.modelEstimate}</span>
          <strong>{formatApproximateGrams(initialMass)}</strong>
        </div>
        {portionRangeLabel ? (
          <div>
            <span>{copy.scan.estimateRange}</span>
            <strong>{portionRangeLabel}</strong>
          </div>
        ) : null}
        <div>
          <span>{copy.scan.activeMass}</span>
          <strong>{formatGrams(activeMass)}</strong>
        </div>
      </div>

      <div className="nutrition-row" aria-label={copy.scan.nutritionLabel}>
        <span>
          <strong>{formatDecimal(item.calories, 0)}</strong>
          <small>{copy.scan.caloriesUnit}</small>
        </span>
        <span>
          <strong>{formatDecimal(item.protein, 1)}</strong>
          <small>{copy.scan.protein}</small>
        </span>
        <span>
          <strong>{formatDecimal(item.fat, 1)}</strong>
          <small>{copy.scan.fat}</small>
        </span>
        <span>
          <strong>{formatDecimal(item.carbs, 1)}</strong>
          <small>{copy.scan.carbs}</small>
        </span>
      </div>

      <div className="correction-grid">
        <div className="correction-grid__row">
          <TextField
            label={copy.scan.checkedMass}
            min="1"
            name={`mass-${item.id}`}
            onChange={handleMassChange}
            step="1"
            type="number"
            value={massDraft}
          />
          <Button
            disabled={isSaving || !massDraft}
            icon={<Check aria-hidden="true" size={18} />}
            onClick={onSaveMass}
            variant="secondary"
          >
            {isSaving ? copy.common.saving : copy.common.save}
          </Button>
        </div>

        <div className="correction-grid__row">
          <TextField
            label={copy.scan.replaceFood}
            name={`food-${item.id}`}
            onChange={handleFoodQueryChange}
            placeholder={copy.scan.foodPlaceholder}
            type="search"
            value={foodQuery}
          />
          <Button
            disabled={isSearching || foodQuery.trim().length < 2}
            icon={<Search aria-hidden="true" size={18} />}
            onClick={onFoodSearch}
            variant="secondary"
          >
            {isSearching ? copy.common.searching : copy.common.search}
          </Button>
        </div>

        {foodOptions.length > 0 ? (
          <div className="food-search-results" aria-label={copy.scan.foundFoodsLabel}>
            {foodOptions.map((food) => (
              <button key={food.id} type="button" onClick={() => onSelectFood(food)}>
                <span>{getFoodSearchDisplayName(food)}</span>
                {food.category ? <small>{food.category.name}</small> : null}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <Button
        className="scan-item-card__remove"
        disabled={isSaving}
        icon={<Trash2 aria-hidden="true" size={18} />}
        onClick={onRemove}
        variant="ghost"
      >
        {copy.common.remove}
      </Button>
    </article>
  );
}
