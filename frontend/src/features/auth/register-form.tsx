"use client";

import { MailCheck, RefreshCw, UserPlus } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { authApi } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export function RegisterForm() {
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);
  const [resendCompleted, setResendCompleted] = useState(false);

  async function handleResend() {
    if (!registeredEmail) {
      return;
    }
    setIsResending(true);
    setError(null);
    try {
      await authApi.resendVerification(registeredEmail);
      setResendCompleted(true);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsResending(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);

    try {
      const email = String(formData.get("email") ?? "");
      await authApi.register({
        email,
        password: String(formData.get("password") ?? ""),
        display_name: String(formData.get("display_name") ?? ""),
        preferred_language: String(formData.get("preferred_language") ?? "ru") === "en" ? "en" : "ru",
      });
      setRegisteredEmail(email);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (registeredEmail) {
    return (
      <section className="auth-form auth-status" aria-live="polite">
        <MailCheck aria-hidden="true" size={32} />
        <h1>{copy.auth.registrationPendingTitle}</h1>
        <p>{copy.auth.registrationPendingDescription}</p>
        <strong className="auth-status__email">{registeredEmail}</strong>
        {resendCompleted ? <p className="form-success">{copy.auth.resendCompleted}</p> : null}
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        <Button
          disabled={isResending}
          icon={<RefreshCw aria-hidden="true" size={18} />}
          onClick={() => void handleResend()}
          variant="secondary"
        >
          {isResending ? copy.common.loading : copy.auth.resendAction}
        </Button>
        <Link className="button button--primary" href="/login">
          {copy.auth.goToLogin}
        </Link>
      </section>
    );
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <header>
        <h1>{copy.auth.registerTitle}</h1>
        <p>{copy.auth.registerSubtitle}</p>
      </header>

      <TextField
        autoComplete="name"
        label={copy.auth.displayName}
        name="display_name"
        type="text"
      />
      <TextField
        autoComplete="email"
        label={copy.auth.email}
        name="email"
        required
        type="email"
      />
      <TextField
        autoComplete="new-password"
        label={copy.auth.password}
        minLength={8}
        name="password"
        required
        type="password"
      />
      <SelectField
        defaultValue="ru"
        label={copy.auth.preferredLanguage}
        name="preferred_language"
        options={[
          { value: "ru", label: "Русский" },
          { value: "en", label: "English" },
        ]}
      />

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <Button
        disabled={isSubmitting}
        icon={<UserPlus aria-hidden="true" size={18} />}
        type="submit"
      >
        {isSubmitting ? copy.common.loading : copy.auth.registerAction}
      </Button>

      <p className="auth-form__footer">
        {copy.auth.hasAccount} <Link href="/login">{copy.auth.goToLogin}</Link>
      </p>
    </form>
  );
}
