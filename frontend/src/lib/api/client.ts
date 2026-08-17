import { API_BASE_URL } from "@/lib/config";
import { clearCsrfToken, getCachedCsrfToken, rememberCsrfToken } from "@/lib/csrf";

import { createApiError } from "./errors";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type JsonBody = Record<string, unknown> | unknown[];

type RequestBody = JsonBody | FormData | null;

type ApiRequestOptions = {
  method?: HttpMethod;
  body?: RequestBody;
  headers?: HeadersInit;
  signal?: AbortSignal;
  skipCsrf?: boolean;
};

const UNSAFE_METHODS = new Set<HttpMethod>(["POST", "PUT", "PATCH", "DELETE"]);

export async function apiRequest<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  const method = options.method ?? "GET";
  const headers = new Headers(options.headers);
  let body: BodyInit | undefined;

  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined && options.body !== null) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  if (UNSAFE_METHODS.has(method) && !options.skipCsrf) {
    headers.set("X-CSRFToken", await ensureCsrfToken());
  }

  const response = await fetch(buildUrl(path), {
    method,
    headers,
    body,
    signal: options.signal,
    credentials: "include",
  });

  if (response.status === 204) {
    return undefined as TResponse;
  }

  const payload = await parseJson(response);

  if (!response.ok) {
    throw createApiError(response.status, payload);
  }

  return payload as TResponse;
}

export async function ensureCsrfToken(): Promise<string> {
  const cachedToken = getCachedCsrfToken();
  if (cachedToken) {
    return cachedToken;
  }

  const response = await fetch(buildUrl("/api/v1/auth/csrf/"), {
    method: "GET",
    credentials: "include",
  });
  const payload = await parseJson(response);

  if (!response.ok || !isCsrfResponse(payload)) {
    clearCsrfToken();
    throw createApiError(response.status, payload);
  }

  rememberCsrfToken(payload.csrf_token);
  return payload.csrf_token;
}

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return { code: "invalid_json_response" };
  }
}

function isCsrfResponse(payload: unknown): payload is { csrf_token: string } {
  return (
    typeof payload === "object" &&
    payload !== null &&
    "csrf_token" in payload &&
    typeof payload.csrf_token === "string"
  );
}
