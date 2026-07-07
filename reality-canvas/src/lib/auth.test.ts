import { beforeEach, describe, expect, it } from "vitest";
import { checkPassword, isAuthenticated, setAuthenticated } from "./auth";

describe("checkPassword", () => {
  it("accepts the default demo password", () => {
    expect(checkPassword("Winniio-2019")).toBe(true);
  });
  it("rejects anything else", () => {
    expect(checkPassword("wrong")).toBe(false);
  });
});

describe("session persistence", () => {
  beforeEach(() => sessionStorage.clear());

  it("is unauthenticated by default", () => {
    expect(isAuthenticated()).toBe(false);
  });

  it("persists auth after setAuthenticated()", () => {
    setAuthenticated();
    expect(isAuthenticated()).toBe(true);
  });
});
