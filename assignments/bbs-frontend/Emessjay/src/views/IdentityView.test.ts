// The exact rules a frontend username must satisfy before we even
// hit the server.  Mirrors A2's Pydantic constraint
// (min_length=3, max_length=20, pattern=^[a-zA-Z0-9_]+$).

import { describe, it, expect } from "vitest";
import { usernameValidity } from "./IdentityView";

describe("usernameValidity", () => {
  it.each([
    ["", false],
    ["ab", false],
    ["abc", true],
    ["alice_42", true],
    ["A_VALID_NAME_19chars", true],
    ["a".repeat(20), true],
    ["a".repeat(21), false],
    ["has-hyphen", false],
    ["has space", false],
    ["has.dot", false],
    ["emoji🙂", false],
    ["___", true],
    ["123", true],
  ])("usernameValidity(%j).ok === %s", (input, expected) => {
    expect(usernameValidity(input).ok).toBe(expected);
  });

  it("returns a helpful reason for too-short usernames", () => {
    expect(usernameValidity("ab").reason).toMatch(/at least 3/i);
  });

  it("returns a regex-flavoured reason when the format is wrong", () => {
    expect(usernameValidity("has space").reason).toMatch(/letters, digits/i);
  });

  it("returns reason=null for an empty string (input has not been typed yet)", () => {
    expect(usernameValidity("").reason).toBeNull();
  });
});
