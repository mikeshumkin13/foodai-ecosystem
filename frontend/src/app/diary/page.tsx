import { CalendarDays, Plus } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { PageHeading } from "@/components/page-heading";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { TextField } from "@/components/ui/text-field";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function DiaryPage() {
  const today = new Date().toISOString().slice(0, 10);

  return (
    <AppShell>
      <PageHeading title={copy.diary.title} subtitle={copy.diary.subtitle} />

      <section className="toolbar" aria-label={copy.diary.title}>
        <TextField defaultValue={today} label={copy.diary.date} name="date" type="date" />
        <Button icon={<Plus aria-hidden="true" size={18} />} variant="secondary">
          {copy.diary.addMeal}
        </Button>
      </section>

      <Card className="panel panel--wide">
        <div className="panel__media-icon">
          <CalendarDays aria-hidden="true" size={28} strokeWidth={1.8} />
        </div>
        <EmptyState title={copy.diary.emptyTitle} description={copy.diary.emptyDescription} />
      </Card>
    </AppShell>
  );
}
