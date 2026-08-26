"use client";

import { CheckCircle2, MailCheck, RefreshCw } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import { authApi } from "@/lib/api/auth";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

type VerificationStatus = "verifying" | "verified" | "failed";

export function EmailVerificationPanel() {
  const [status, setStatus] = useState<VerificationStatus>("verifying");
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [isResending, setIsResending] = useState(false);
  const [resendCompleted, setResendCompleted] = useState(false);
  const hasStarted = useRef(false);

  useEffect(() => {
    if (hasStarted.current) {
      return;
    }
    hasStarted.current = true;

    const searchParams = new URLSearchParams(window.location.search);
    const tokenId = searchParams.get("token_id");
    const token = searchParams.get("token");
    if (!tokenId || !token) {
      setStatus("failed");
      setError(copy.auth.verificationInvalid);
      return;
    }

    authApi
      .verifyEmail({ token_id: tokenId, token })
      .then(() => setStatus("verified"))
      .catch((requestError: unknown) => {
        setStatus("failed");
        setError(getErrorMessage(requestError));
      });
  }, []);

  async function handleResend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsResending(true);
    setError(null);
    try {
      await authApi.resendVerification(email);
      setResendCompleted(true);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsResending(false);
    }
  }

  if (status === "verifying") {
    return (
      <section className="auth-form auth-status" aria-live="polite">
        <MailCheck aria-hidden="true" size={32} />
        <h1>{copy.auth.verifyingTitle}</h1>
        <p>{copy.auth.verifyingDescription}</p>
      </section>
    );
  }

  if (status === "verified") {
    return (
      <section className="auth-form auth-status" aria-live="polite">
        <CheckCircle2 aria-hidden="true" size={32} />
        <h1>{copy.auth.verifiedTitle}</h1>
        <p>{copy.auth.verifiedDescription}</p>
        <Link className="button button--primary" href="/login">
          {copy.auth.goToLogin}
        </Link>
      </section>
    );
  }

  return (
    <form className="auth-form" onSubmit={handleResend}>
      <header>
        <h1>{copy.auth.verificationFailedTitle}</h1>
        <p>{copy.auth.verificationFailedDescription}</p>
      </header>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {resendCompleted ? <p className="form-success">{copy.auth.resendCompleted}</p> : null}
      <TextField
        autoComplete="email"
        label={copy.auth.email}
        name="email"
        onChange={(event) => setEmail(event.target.value)}
        required
        type="email"
        value={email}
      />
      <Button
        disabled={isResending || email.length === 0}
        icon={<RefreshCw aria-hidden="true" size={18} />}
        type="submit"
      >
        {isResending ? copy.common.loading : copy.auth.resendAction}
      </Button>
      <p className="auth-form__footer">
        <Link href="/login">{copy.auth.goToLogin}</Link>
      </p>
    </form>
  );
}
