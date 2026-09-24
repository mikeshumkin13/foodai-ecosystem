import { AuthShell } from "@/components/auth-shell";
import { PasswordForm } from "@/features/auth/password-form";

export default function PasswordResetPage() {
  return <AuthShell><PasswordForm mode="reset" /></AuthShell>;
}
