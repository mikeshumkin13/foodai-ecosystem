"use client";

import { LogIn } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import { authApi } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export function LoginForm() {
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);

    try {
      await authApi.login({
        email: String(formData.get("email") ?? ""),
        password: String(formData.get("password") ?? ""),
      });
      window.location.assign("/dashboard");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <header>
        <h1>{copy.auth.loginTitle}</h1>
        <p>{copy.auth.loginSubtitle}</p>
      </header>

      <TextField
        autoComplete="email"
        label={copy.auth.email}
        name="email"
        required
        type="email"
      />
      <TextField
        autoComplete="current-password"
        label={copy.auth.password}
        minLength={8}
        name="password"
        required
        type="password"
      />

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <Button
        disabled={isSubmitting}
        icon={<LogIn aria-hidden="true" size={18} />}
        type="submit"
      >
        {isSubmitting ? copy.common.loading : copy.auth.loginAction}
      </Button>

      <p className="auth-form__footer">
        {copy.auth.noAccount} <Link href="/register">{copy.auth.goToRegister}</Link>
      </p>
    </form>
  );
}
