import { describe, expect, it } from "vitest";

import { getSafeNextPath } from "./redirects";

describe("getSafeNextPath", () => {
  it("keeps same-site application paths", () => {
    expect(getSafeNextPath("/diary?date=2026-08-26")).toBe("/diary?date=2026-08-26");
  });

  it.each(["https://example.com", "//example.com", "dashboard", null])(
    "rejects an unsafe redirect value %s",
    (value) => {
      expect(getSafeNextPath(value)).toBe("/dashboard");
    },
  );
});
