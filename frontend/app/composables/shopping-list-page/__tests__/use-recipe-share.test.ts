import { describe, expect, test } from "vitest";
import type { ShoppingListItemOut } from "~/lib/api/types/household";
import { MOCK_ITEM } from "../sub-composables/__tests__/mocks";
import { formatShare, recipeShare, withRecipeShare } from "../use-recipe-share";

function ref(recipeId: string, recipeQuantity: number, recipeScale: number | null = 1) {
  return { id: `ref-${recipeId}`, shoppingListItemId: "item", recipeId, recipeQuantity, recipeScale };
}

function item(quantity: number, refs: ReturnType<typeof ref>[]): ShoppingListItemOut {
  return { ...MOCK_ITEM, quantity, recipeReferences: refs };
}

describe("recipe share", () => {
  test("share is quantity times scale", () => {
    const i = item(7, [ref("gulasch", 2, 2), ref("fajitas", 3)]);
    expect(recipeShare(i, "gulasch")).toBe(4);
    expect(recipeShare(i, "fajitas")).toBe(3);
    expect(recipeShare(i, "unknown")).toBe(0);
  });

  test("setting a share to 0 lowers the total and keeps the reference", () => {
    const i = item(7, [ref("gulasch", 4), ref("fajitas", 3)]);
    const updated = withRecipeShare(i, "gulasch", 0);
    expect(updated.quantity).toBe(3);
    expect(updated.recipeReferences).toHaveLength(2);
    expect(recipeShare(updated, "gulasch")).toBe(0);
    // the original item is untouched
    expect(i.quantity).toBe(7);
  });

  test("raising a share raises the total", () => {
    const updated = withRecipeShare(item(7, [ref("gulasch", 4), ref("fajitas", 3)]), "fajitas", 10);
    expect(updated.quantity).toBe(14);
    expect(recipeShare(updated, "fajitas")).toBe(10);
  });

  test("an amount added by hand is kept", () => {
    // 4 + 3 from recipes, 2 more typed in by hand
    const updated = withRecipeShare(item(9, [ref("gulasch", 4), ref("fajitas", 3)]), "gulasch", 0);
    expect(updated.quantity).toBe(5);
  });

  test("scale is kept so removing the recipe later takes away the new share", () => {
    const updated = withRecipeShare(item(4, [ref("gulasch", 2, 2)]), "gulasch", 3);
    const r = updated.recipeReferences![0]!;
    expect(r.recipeScale).toBe(2);
    expect(r.recipeQuantity).toBe(1.5);
    expect(updated.quantity).toBe(3);
  });

  test("missing or zero scale falls back to 1", () => {
    expect(withRecipeShare(item(2, [ref("gulasch", 2, null)]), "gulasch", 5).recipeReferences![0]!.recipeScale).toBe(1);
    const zero = withRecipeShare(item(0, [ref("gulasch", 2, 0)]), "gulasch", 5);
    expect(zero.recipeReferences![0]!.recipeScale).toBe(1);
    expect(zero.quantity).toBe(5);
  });

  test("never goes below 0", () => {
    expect(withRecipeShare(item(1, [ref("gulasch", 4)]), "gulasch", 0).quantity).toBe(0);
    expect(withRecipeShare(item(4, [ref("gulasch", 4)]), "gulasch", -3).quantity).toBe(0);
  });

  test("format", () => {
    expect(formatShare(2)).toBe("2");
    expect(formatShare(1 / 3)).toBe("0.33");
  });
});
