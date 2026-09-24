import { AuthShell } from "@/components/auth-shell";
import { PasswordResetRequestForm } from "@/features/auth/password-reset-request-form";

export default function ForgotPasswordPage() {
  return <AuthShell><PasswordResetRequestForm /></AuthShell>;
}
