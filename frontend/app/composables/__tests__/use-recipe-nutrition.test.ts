import { describe, expect, test } from "vitest";
import {
  defaultNutritionFilter,
  matchesNutrition,
  nutritionFilterActive,
  parseNutritionFilter,
  recipeIdFilter,
  serializeNutritionFilter,
} from "../use-recipe-nutrition";

const bowl = { calories: 486, protein: 57, carbohydrate: 34, fat: 9 };
const chili = { calories: 750, protein: 52, carbohydrate: 109, fat: 13 };

describe("use-recipe-nutrition", () => {
  test("default filter is inactive and matches everything, even unknown values", () => {
    const filter = defaultNutritionFilter();
    expect(nutritionFilterActive(filter)).toBe(false);
    expect(matchesNutrition(undefined, filter)).toBe(true);
  });

  test("ranges filter per portion", () => {
    const filter = defaultNutritionFilter();
    filter.calories = [0, 600];
    filter.protein = [50, 100];
    expect(matchesNutrition(bowl, filter)).toBe(true);
    expect(matchesNutrition(chili, filter)).toBe(false);
    expect(matchesNutrition({ ...bowl, protein: null }, filter)).toBe(false);
  });

  test("the slider maximum is open-ended", () => {
    const filter = defaultNutritionFilter();
    filter.calories = [700, 1200];
    expect(matchesNutrition({ ...chili, calories: 1450 }, filter)).toBe(true);
    expect(matchesNutrition(bowl, filter)).toBe(false);
  });

  test("url round trip keeps only active ranges and clamps garbage", () => {
    const filter = defaultNutritionFilter();
    filter.calories = [200, 700];
    expect(serializeNutritionFilter(filter)).toBe("calories:200-700");
    expect(parseNutritionFilter("calories:200-700")).toEqual(filter);
    const parsed = parseNutritionFilter("protein:80-20,fat:abc,evil:1-2,carbohydrate:-5-999");
    expect(parsed.protein).toEqual([80, 80]);
    expect(parsed.fat).toEqual(defaultNutritionFilter().fat);
  });

  test("id filter never becomes an empty IN list", () => {
    expect(recipeIdFilter(["a", "b"])).toBe("id IN [\"a\", \"b\"]");
    expect(recipeIdFilter([])).toBe("id IN [\"00000000-0000-0000-0000-000000000000\"]");
  });
});
