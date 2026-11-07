import { describe, expect, test } from "vitest";
import { sortBySupermarket } from "./label-order";

describe("sortBySupermarket", () => {
  test("produce first, frozen after dairy, household last", () => {
    const names = ["Haushalt", "Tiefkühlware", "Milchprodukte", "Konserven", "Obst & Gemüse", "TK", "Fleisch"];
    const sorted = sortBySupermarket(names, n => n);
    expect(sorted[0]).toBe("Obst & Gemüse");
    expect(sorted.at(-1)).toBe("Haushalt");
    expect(sorted.indexOf("Milchprodukte")).toBeLessThan(sorted.indexOf("TK"));
    expect(sorted.indexOf("TK")).toBeLessThan(sorted.indexOf("Konserven"));
  });
});
