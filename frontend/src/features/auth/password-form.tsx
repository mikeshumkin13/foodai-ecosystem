"use client";

import { KeyRound } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import { authApi } from "@/lib/api/auth";
import type { EmailVerificationPayload } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export function PasswordForm({ mode }: { mode: "reset" | "change" }) {
  const [token, setToken] = useState<EmailVerificationPayload | null>(null);
  const [pending, setPending] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "reset") return;
    const params = new URLSearchParams(window.location.search);
    const tokenId = params.get("token_id");
    const secret = params.get("token");
    if (tokenId && secret) {
      setToken({ token_id: tokenId, token: secret });
    } else {
      setError(copy.auth.verificationInvalid);
    }
  }, [mode]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending || (mode === "reset" && (!token || completed))) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const password = String(data.get("new_password") ?? "");
    setCompleted(false);
    if (password !== data.get("confirm_password")) {
      setError(copy.auth.passwordMismatch);
      return;
    }
    setPending(true);
    setError(null);
    try {
      if (mode === "change") {
        await authApi.changePassword(String(data.get("current_password") ?? ""), password);
      } else if (token) {
        await authApi.resetPassword({ ...token, new_password: password });
        setToken(null);
        window.history.replaceState(null, "", window.location.pathname);
      }
      form.reset();
      setCompleted(true);
    } catch (failure) {
      setError(getErrorMessage(failure));
    } finally {
      setPending(false);
    }
  }

  const title = mode === "change" ? copy.auth.changePasswordTitle : copy.auth.resetPasswordTitle;
  const disabled = pending || (mode === "reset" && (!token || completed));

  return (
    <form className={mode === "reset" ? "auth-form" : "password-form"} onSubmit={handleSubmit}>
      {mode === "reset" ? <h1>{title}</h1> : <h2>{title}</h2>}
      {mode === "change" ? (
        <TextField label={copy.auth.currentPassword} name="current_password" type="password" autoComplete="current-password" required disabled={pending} />
      ) : null}
      <TextField label={copy.auth.newPassword} name="new_password" type="password" autoComplete="new-password" minLength={8} required disabled={disabled} />
      <TextField label={copy.auth.confirmPassword} name="confirm_password" type="password" autoComplete="new-password" minLength={8} required disabled={disabled} />
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {completed ? <p className="form-success" role="status">{mode === "change" ? copy.auth.changePasswordCompleted : copy.auth.resetPasswordCompleted}</p> : null}
      <Button type="submit" disabled={disabled} icon={<KeyRound aria-hidden="true" size={18} />}>
        {pending ? copy.common.loading : mode === "change" ? copy.auth.changePasswordAction : copy.auth.resetPasswordAction}
      </Button>
      {mode === "reset" ? (
        <p className="auth-form__footer"><Link href="/login">{copy.auth.goToLogin}</Link>{" · "}<Link href="/forgot-password">{copy.auth.resetRequestAction}</Link></p>
      ) : null}
    </form>
  );
}
