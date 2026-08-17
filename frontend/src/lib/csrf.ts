let csrfTokenCache: string | null = null;

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const cookie = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${encodeURIComponent(name)}=`));

  if (!cookie) {
    return null;
  }

  return decodeURIComponent(cookie.split("=").slice(1).join("="));
}

export function getCachedCsrfToken(): string | null {
  return csrfTokenCache ?? readCookie("csrftoken");
}

export function rememberCsrfToken(token: string): void {
  csrfTokenCache = token;
}

export function clearCsrfToken(): void {
  csrfTokenCache = null;
}
