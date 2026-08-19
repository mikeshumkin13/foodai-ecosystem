import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PageHeading } from "@/components/page-heading";
import { LoadingState } from "@/components/ui/loading-state";
import { DashboardPanel } from "@/features/dashboard/dashboard-panel";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function DashboardPage() {
  return (
    <AppShell>
      <PageHeading title={copy.dashboard.title} subtitle={copy.dashboard.subtitle} />
      <Suspense fallback={<LoadingState label={copy.common.loading} />}>
        <DashboardPanel />
      </Suspense>
    </AppShell>
  );
}
