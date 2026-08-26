"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { ApiError } from "@/lib/api/errors";
import { authApi } from "@/lib/api/auth";
import type { UserSummary } from "@/lib/api/types";
import { AUTHENTICATION_REQUIRED_EVENT } from "@/lib/auth/session-events";

type AuthSessionStatus = "loading" | "authenticated" | "anonymous" | "unavailable";

type AuthSessionContextValue = {
  status: AuthSessionStatus;
  user: UserSummary | null;
  reload: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthSessionContext = createContext<AuthSessionContextValue | null>(null);
const SESSION_REFRESH_INTERVAL_MS = 30 * 60 * 1000;

export function AuthSessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthSessionStatus>("loading");
  const [user, setUser] = useState<UserSummary | null>(null);

  const reload = useCallback(async () => {
    setStatus("loading");
    try {
      const currentUser = await authApi.me();
      setUser(currentUser);
      setStatus("authenticated");
    } catch (error) {
      setUser(null);
      setStatus(isAuthenticationError(error) ? "anonymous" : "unavailable");
    }
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    setStatus("anonymous");
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (status !== "authenticated") {
      return;
    }

    const refreshSession = window.setInterval(() => {
      void authApi
        .refresh()
        .then((response) => setUser(response.user))
        .catch((error: unknown) => {
          if (!isAuthenticationError(error)) {
            setStatus("unavailable");
          }
        });
    }, SESSION_REFRESH_INTERVAL_MS);

    return () => window.clearInterval(refreshSession);
  }, [status]);

  useEffect(() => {
    function handleAuthenticationRequired() {
      setUser(null);
      setStatus("anonymous");
    }

    window.addEventListener(AUTHENTICATION_REQUIRED_EVENT, handleAuthenticationRequired);
    return () => {
      window.removeEventListener(AUTHENTICATION_REQUIRED_EVENT, handleAuthenticationRequired);
    };
  }, []);

  const value = useMemo(
    () => ({ status, user, reload, logout }),
    [logout, reload, status, user],
  );

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

export function useAuthSession(): AuthSessionContextValue {
  const context = useContext(AuthSessionContext);
  if (!context) {
    throw new Error("useAuthSession must be used inside AuthSessionProvider");
  }
  return context;
}

function isAuthenticationError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}
