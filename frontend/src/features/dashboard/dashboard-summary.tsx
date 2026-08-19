import {
  Activity,
  ArrowRight,
  BookOpenText,
  Camera,
  Flame,
  ListChecks,
  Salad,
  Scale,
  Target,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import type { DiaryDay, Meal } from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

import {
  getMealItemCountLabel,
  getMealTimeLabel,
  getMealTitle,
  getMealTotals,
  getNutritionSummaryLabel,
} from "../diary/meal-utils";
import { formatDecimal } from "../scan/scan-format";
import type { DashboardMetrics } from "./dashboard-metrics";

const copy = messages.ru;

type DashboardSummaryProps = {
  diaryDay: DiaryDay | null;
  metrics: DashboardMetrics;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
};

const metricIcons = {
  caloriesConsumed: Flame,
  calorieTarget: Target,
  protein: Scale,
  fat: Activity,
  carbs: Salad,
  mealsToday: ListChecks,
};

export function DashboardSummary({
  diaryDay,
  metrics,
  isLoading,
  error,
  onRefresh,
}: DashboardSummaryProps) {
  const calorieProgress =
    metrics.calorieTarget && metrics.calorieTarget > 0
      ? Math.min((metrics.caloriesConsumed / metrics.calorieTarget) * 100, 100)
      : 0;

  return (
    <div className="dashboard-layout">
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <section className="metrics-grid metrics-grid--dashboard" aria-label={copy.dashboard.title}>
        <DashboardMetric
          icon={metricIcons.caloriesConsumed}
          label={copy.dashboard.caloriesConsumed}
          unit={copy.scan.caloriesUnit}
          value={formatDecimal(metrics.caloriesConsumed, 0)}
        />
        <DashboardMetric
          icon={metricIcons.calorieTarget}
          label={copy.dashboard.calorieTarget}
          unit={copy.scan.caloriesUnit}
          value={metrics.calorieTarget ? `≈ ${formatDecimal(metrics.calorieTarget, 0)}` : "—"}
        />
        <DashboardMetric
          icon={metricIcons.protein}
          label={copy.dashboard.protein}
          unit="г"
          value={formatDecimal(metrics.protein, 1)}
        />
        <DashboardMetric
          icon={metricIcons.fat}
          label={copy.dashboard.fat}
          unit="г"
          value={formatDecimal(metrics.fat, 1)}
        />
        <DashboardMetric
          icon={metricIcons.carbs}
          label={copy.dashboard.carbs}
          unit="г"
          value={formatDecimal(metrics.carbs, 1)}
        />
        <DashboardMetric
          icon={metricIcons.mealsToday}
          label={copy.dashboard.mealsToday}
          unit={copy.dashboard.mealsUnit}
          value={formatDecimal(metrics.mealsToday, 0)}
        />
      </section>

      <section className="dashboard-progress" aria-label={copy.dashboard.calorieProgress}>
        <div className="dashboard-progress__header">
          <div>
            <h2>{copy.dashboard.calorieProgress}</h2>
            <p>{metrics.calorieTarget ? copy.dashboard.targetEstimated : copy.dashboard.targetMissing}</p>
          </div>
          <Button onClick={onRefresh} variant="secondary" disabled={isLoading}>
            {copy.common.refresh}
          </Button>
        </div>
        <div className="progress-bar" aria-hidden="true">
          <span style={{ width: `${calorieProgress}%` }} />
        </div>
        <small>
          {formatDecimal(metrics.caloriesConsumed, 0)} /{" "}
          {metrics.calorieTarget ? formatDecimal(metrics.calorieTarget, 0) : "—"} {copy.scan.caloriesUnit}
        </small>
      </section>

      <section className="content-grid">
        <Card className="panel">
          <header className="panel__header">
            <h2>{copy.dashboard.diaryToday}</h2>
            {isLoading ? <LoadingState label={copy.common.loading} /> : null}
          </header>

          {diaryDay && diaryDay.meals.length > 0 ? (
            <div className="dashboard-meal-list">
              {diaryDay.meals.map((meal) => (
                <DashboardMealRow key={meal.id} meal={meal} />
              ))}
            </div>
          ) : (
            <EmptyState title={copy.common.empty} description={copy.dashboard.emptyDiary} />
          )}
        </Card>

        <Card className="panel">
          <header className="panel__header">
            <h2>{copy.dashboard.quickActions}</h2>
          </header>
          <div className="quick-actions">
            <Link className="button button--primary" href="/diary">
              <BookOpenText aria-hidden="true" size={18} />
              <span>{copy.dashboard.addManualMeal}</span>
            </Link>
            <Link className="button button--secondary" href="/scan">
              <Camera aria-hidden="true" size={18} />
              <span>{copy.dashboard.addViaScan}</span>
            </Link>
          </div>
        </Card>
      </section>
    </div>
  );
}

function DashboardMetric({
  icon: Icon,
  label,
  value,
  unit,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <Card className="metric-card">
      <div className="metric-card__icon">
        <Icon aria-hidden="true" size={20} strokeWidth={1.9} />
      </div>
      <span>{label}</span>
      <strong>
        {value}
        <small>{unit}</small>
      </strong>
    </Card>
  );
}

function DashboardMealRow({ meal }: { meal: Meal }) {
  const totals = getMealTotals(meal.items);

  return (
    <Link className="dashboard-meal-row" href={`/diary?date=${meal.logged_at.slice(0, 10)}`}>
      <div>
        <span>{getMealTimeLabel(meal.logged_at)}</span>
        <strong>{getMealTitle(meal)}</strong>
      </div>
      <div>
        <small>{getMealItemCountLabel(meal.items.length)}</small>
        <small>{getNutritionSummaryLabel(totals)}</small>
      </div>
      <ArrowRight aria-hidden="true" size={17} />
    </Link>
  );
}
