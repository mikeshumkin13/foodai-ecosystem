import { AppShell } from "@/components/app-shell";
import { PageHeading } from "@/components/page-heading";
import { PrivacyCenterPanel } from "@/features/privacy/privacy-center-panel";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function PrivacyPage() {
  return (
    <AppShell>
      <PageHeading title={copy.privacy.title} subtitle={copy.privacy.subtitle} />
      <PrivacyCenterPanel />
    </AppShell>
  );
}
