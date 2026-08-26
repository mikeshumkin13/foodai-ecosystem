"use client";

import {
  BarChart3,
  BookOpenText,
  Camera,
  LogOut,
  MessageCircle,
  RefreshCw,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { useAuthSession } from "@/components/auth-session-provider";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/loading-state";
import { getCurrentPathWithQuery } from "@/lib/auth/redirects";
import { messages } from "@/lib/i18n/messages";
import { cn } from "@/lib/utils";

const copy = messages.ru;

const navItems = [
  { href: "/dashboard", label: copy.nav.dashboard, icon: BarChart3 },
  { href: "/diary", label: copy.nav.diary, icon: BookOpenText },
  { href: "/scan", label: copy.nav.scan, icon: Camera },
  { href: "/coach", label: copy.nav.coach, icon: MessageCircle },
  { href: "/profile", label: copy.nav.profile, icon: UserRound },
  { href: "/privacy", label: copy.nav.privacy, icon: ShieldCheck },
];

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, reload, status, user } = useAuthSession();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    if (status === "anonymous") {
      const nextPath = encodeURIComponent(getCurrentPathWithQuery());
      router.replace(`/login?next=${nextPath}`);
    }
  }, [router, status]);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await logout();
      router.replace("/login");
    } finally {
      setIsLoggingOut(false);
    }
  }

  if (status === "loading" || status === "anonymous") {
    return (
      <main className="session-state">
        <LoadingState label={copy.auth.sessionChecking} />
      </main>
    );
  }

  if (status === "unavailable") {
    return (
      <main className="session-state">
        <p className="form-error" role="alert">{copy.auth.sessionUnavailable}</p>
        <Button
          icon={<RefreshCw aria-hidden="true" size={18} />}
          onClick={() => void reload()}
          variant="secondary"
        >
          {copy.common.retry}
        </Button>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Основная навигация">
        <Link className="brand" href="/dashboard">
          <span className="brand__mark" aria-hidden="true" />
          <span>
            <strong>{copy.app.name}</strong>
            <small>{copy.app.tagline}</small>
          </span>
        </Link>

        <nav className="sidebar__nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;

            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={cn("nav-link", active && "nav-link--active")}
                href={item.href}
                key={item.href}
              >
                <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar__account">
          <span>{user?.email}</span>
          <Button
            disabled={isLoggingOut}
            icon={<LogOut aria-hidden="true" size={18} />}
            onClick={() => void handleLogout()}
            variant="ghost"
          >
            {isLoggingOut ? copy.common.loading : copy.auth.logoutAction}
          </Button>
        </div>
      </aside>

      <main className="app-main">{children}</main>

      <nav className="mobile-nav" aria-label="Основная навигация">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;

          return (
            <Link
              aria-current={active ? "page" : undefined}
              className={cn("mobile-nav__link", active && "mobile-nav__link--active")}
              href={item.href}
              key={item.href}
            >
              <Icon aria-hidden="true" size={20} strokeWidth={1.9} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
