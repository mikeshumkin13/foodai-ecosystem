import { AppShell } from "@/components/app-shell";
import { PageHeading } from "@/components/page-heading";
import { ScanUploadPanel } from "@/features/scan/scan-upload-panel";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function ScanPage() {
  return (
    <AppShell>
      <PageHeading title={copy.scan.title} subtitle={copy.scan.subtitle} />
      <ScanUploadPanel />
    </AppShell>
  );
}
