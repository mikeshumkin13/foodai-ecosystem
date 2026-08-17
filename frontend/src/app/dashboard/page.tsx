import { Activity, Flame, Salad, Scale } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

const metrics = [
  { label: copy.dashboard.calories, value: "0", unit: "kcal", icon: Flame },
  { label: copy.dashboard.protein, value: "0", unit: "g", icon: Scale },
  { label: copy.dashboard.fat, value: "0", unit: "g", icon: Activity },
  { label: copy.dashboard.carbs, value: "0", unit: "g", icon: Salad },
];

export default function DashboardPage() {
  return (
    <AppShell>
      <PageHeading title={copy.dashboard.title} subtitle={copy.dashboard.subtitle} />

      <section className="metrics-grid" aria-label={copy.dashboard.title}>
        {metrics.map((metric) => {
          const Icon = metric.icon;

          return (
            <Card className="metric-card" key={metric.label}>
              <div className="metric-card__icon">
                <Icon aria-hidden="true" size={20} strokeWidth={1.9} />
              </div>
              <span>{metric.label}</span>
              <strong>
                {metric.value}
                <small>{metric.unit}</small>
              </strong>
            </Card>
          );
        })}
      </section>

      <section className="content-grid">
        <Card className="panel">
          <header className="panel__header">
            <h2>{copy.dashboard.diaryToday}</h2>
            <LoadingState label={copy.common.loading} />
          </header>
          <EmptyState title={copy.common.empty} description={copy.dashboard.emptyDiary} />
        </Card>

        <Card className="panel">
          <header className="panel__header">
            <h2>{copy.dashboard.recentScans}</h2>
          </header>
          <EmptyState title={copy.common.empty} description={copy.dashboard.emptyScans} />
        </Card>
      </section>
    </AppShell>
  );
}
