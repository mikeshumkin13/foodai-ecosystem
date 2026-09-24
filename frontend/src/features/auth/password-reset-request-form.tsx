"use client";

import { Mail } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import { authApi } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export function PasswordResetRequestForm() {
  const [pending, setPending] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const email = String(new FormData(form).get("email") ?? "").trim();
    setPending(true);
    setError(null);
    setCompleted(false);
    try {
      await authApi.requestPasswordReset(email);
      setCompleted(true);
      form.reset();
    } catch (failure) {
      setError(getErrorMessage(failure));
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <h1>{copy.auth.resetRequestTitle}</h1>
      <TextField label={copy.auth.email} name="email" type="email" autoComplete="email" required disabled={pending} />
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {completed ? <p className="form-success" role="status">{copy.auth.resetRequestCompleted}</p> : null}
      <Button type="submit" disabled={pending} icon={<Mail aria-hidden="true" size={18} />}>
        {pending ? copy.common.loading : copy.auth.resetRequestAction}
      </Button>
      <p className="auth-form__footer"><Link href="/login">{copy.auth.goToLogin}</Link></p>
    </form>
  );
}
