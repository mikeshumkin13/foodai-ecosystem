import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { LoadingState } from "@/components/ui/loading-state";
import { PageHeading } from "@/components/page-heading";
import { DiaryDayPanel } from "@/features/diary/diary-day-panel";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function DiaryPage() {
  return (
    <AppShell>
      <PageHeading title={copy.diary.title} subtitle={copy.diary.subtitle} />
      <Suspense fallback={<LoadingState label={copy.common.loading} />}>
        <DiaryDayPanel />
      </Suspense>
    </AppShell>
  );
}
