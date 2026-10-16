import { describe, expect, test } from "vitest";
import { shortLabel, toPeople } from "./people";

describe("planner people", () => {
  test("single initial when unique", () => {
    expect(toPeople([{ id: "1", name: "Jakob" }, { id: "2", name: "Sanja" }]).map(p => p.label)).toEqual(["J", "S"]);
  });

  test("shortest unique prefix when initials collide", () => {
    const labels = toPeople(["Jakob", "Jason", "Sarah", "Sammy", "Sanja", "Bob"].map((name, i) => ({ id: String(i), name }))).map(p => p.label);
    expect(labels).toEqual(["Jak", "Jas", "Sar", "Sam", "San", "B"]);
    expect(new Set(labels).size).toBe(labels.length);
  });

  test("identical names stay distinguishable", () => {
    const labels = toPeople([{ id: "1", name: "Anna" }, { id: "2", name: "Anna" }]).map(p => p.label);
    expect(labels).toEqual(["An", "An2"]);
    expect(shortLabel("Ann", ["Anna"])).toBe("An");
  });

  test("colours cycle through person tokens", () => {
    const people = toPeople(Array.from({ length: 7 }, (_, i) => ({ id: String(i), name: `P${i}` })));
    expect(people[0]!.color).toBe("var(--fork-person-1)");
    expect(people[6]!.color).toBe("var(--fork-person-1)");
  });
});
