import { AuthShell } from "@/components/auth-shell";
import { EmailVerificationPanel } from "@/features/auth/email-verification-panel";

export default function EmailVerificationPage() {
  return (
    <AuthShell>
      <EmailVerificationPanel />
    </AuthShell>
  );
}
