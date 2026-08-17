"use client";

import { BarChart3, BookOpenText, Camera, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { messages } from "@/lib/i18n/messages";
import { cn } from "@/lib/utils";

const copy = messages.ru;

const navItems = [
  { href: "/dashboard", label: copy.nav.dashboard, icon: BarChart3 },
  { href: "/diary", label: copy.nav.diary, icon: BookOpenText },
  { href: "/scan", label: copy.nav.scan, icon: Camera },
  { href: "/profile", label: copy.nav.profile, icon: UserRound },
];

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();

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
