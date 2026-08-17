import { describe, expect, it } from "vitest";

import { cn } from "./utils";

describe("cn", () => {
  it("joins truthy class names", () => {
    expect(cn("button", false, null, undefined, "button--primary")).toBe(
      "button button--primary",
    );
  });
});
