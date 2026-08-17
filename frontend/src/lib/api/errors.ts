export type ApiErrorDetails = Record<string, unknown> | string | string[] | null;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ApiErrorDetails;

  constructor({
    status,
    code,
    details,
  }: {
    status: number;
    code: string;
    details: ApiErrorDetails;
  }) {
    super(code);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return ERROR_MESSAGES[error.code] ?? ERROR_MESSAGES.default;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return ERROR_MESSAGES.default;
}

export function createApiError(status: number, payload: unknown): ApiError {
  if (isErrorObject(payload)) {
    const code = extractErrorCode(payload);
    return new ApiError({ status, code, details: payload });
  }

  return new ApiError({ status, code: "request_failed", details: null });
}

function extractErrorCode(payload: Record<string, unknown>): string {
  if (typeof payload.code === "string") {
    return payload.code;
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  for (const value of Object.values(payload)) {
    if (Array.isArray(value) && typeof value[0] === "string") {
      return value[0];
    }
  }

  return "request_failed";
}

function isErrorObject(payload: unknown): payload is Record<string, unknown> {
  return typeof payload === "object" && payload !== null;
}

const ERROR_MESSAGES: Record<string, string> = {
  csrf_failed: "Сессия устарела. Обновите страницу и повторите действие.",
  email_already_registered: "Этот email уже зарегистрирован.",
  invalid_credentials: "Email или пароль указаны неверно.",
  request_failed: "Не удалось выполнить запрос. Повторите попытку позже.",
  default: "Что-то пошло не так. Повторите попытку позже.",
};
