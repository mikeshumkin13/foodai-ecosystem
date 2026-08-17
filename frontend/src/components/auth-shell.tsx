import Link from "next/link";
import type { ReactNode } from "react";

import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

type AuthShellProps = {
  children: ReactNode;
};

export function AuthShell({ children }: AuthShellProps) {
  return (
    <main className="auth-page">
      <section className="auth-page__intro" aria-labelledby="auth-brand-title">
        <Link className="brand brand--light" href="/dashboard">
          <span className="brand__mark" aria-hidden="true" />
          <span>
            <strong id="auth-brand-title">{copy.app.productName}</strong>
            <small>{copy.app.tagline}</small>
          </span>
        </Link>
      </section>
      <section className="auth-page__panel">{children}</section>
    </main>
  );
}
