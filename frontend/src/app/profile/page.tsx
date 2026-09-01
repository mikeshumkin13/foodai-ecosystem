import { AppShell } from "@/components/app-shell";
import { PageHeading } from "@/components/page-heading";
import { NutritionProfileForm } from "@/features/profile/nutrition-profile-form";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function ProfilePage() {
  return (
    <AppShell>
      <PageHeading title={copy.profile.title} subtitle={copy.profile.subtitle} />
      <NutritionProfileForm />
    </AppShell>
  );
}
