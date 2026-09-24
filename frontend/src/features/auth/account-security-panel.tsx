"use client";

import { LogOut } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { useAuthSession } from "@/components/auth-session-provider";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";
import { PasswordForm } from "./password-form";

const copy = messages.ru;

export function AccountSecurityPanel() {
  const { logout } = useAuthSession();
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogout() {
    setPending(true);
    setError(null);
    try {
      await logout();
      router.replace("/login");
    } catch (failure) {
      setError(getErrorMessage(failure));
    } finally {
      setPending(false);
    }
  }

  return (
    <section>
      <PasswordForm mode="change" />
      <div className="profile-form-actions">
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        <Button variant="secondary" onClick={() => void handleLogout()} disabled={pending} icon={<LogOut aria-hidden="true" size={18} />}>
          {pending ? copy.common.loading : copy.auth.logoutAction}
        </Button>
      </div>
    </section>
  );
}
