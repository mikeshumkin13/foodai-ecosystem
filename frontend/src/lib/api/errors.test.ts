import { describe, expect, it } from "vitest";

import { ApiError, createApiError, getErrorMessage } from "./errors";

describe("API error handling", () => {
  it("extracts stable backend error codes", () => {
    const error = createApiError(400, { email: ["email_already_registered"] });

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("email_already_registered");
    expect(getErrorMessage(error)).toBe("Этот email уже зарегистрирован.");
  });

  it("falls back to a generic message for unknown errors", () => {
    const error = createApiError(502, null);

    expect(error.code).toBe("request_failed");
    expect(getErrorMessage(error)).toBe("Не удалось выполнить запрос. Повторите попытку позже.");
  });
});
