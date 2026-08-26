import { AppShell } from "@/components/app-shell";
import { PageHeading } from "@/components/page-heading";
import { NutritionCoachPanel } from "@/features/coach/nutrition-coach-panel";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function CoachPage() {
  return (
    <AppShell>
      <PageHeading title={copy.coach.title} subtitle={copy.coach.subtitle} />
      <NutritionCoachPanel />
    </AppShell>
  );
}
