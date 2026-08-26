export function getSafeNextPath(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/dashboard";
  }

  return value;
}

export function getCurrentPathWithQuery(): string {
  if (typeof window === "undefined") {
    return "/dashboard";
  }

  return `${window.location.pathname}${window.location.search}`;
}
