import type { ShoppingListItemOut } from "~/lib/api/types/household";

/**
 * A shopping list item that came from several recipes keeps one reference per recipe, holding
 * how much of the item that recipe needs. These helpers read and change one recipe's share of an
 * item. Only the shopping list item changes: the recipe itself and how many portions of it are on
 * the list stay as they are.
 */

function roundQuantity(n: number): number {
  return Math.round(n * 1000) / 1000;
}

/** How much of this item the given recipe needs, as it currently stands on the list */
export function recipeShare(item: ShoppingListItemOut, recipeId: string): number {
  const ref = item.recipeReferences?.find(r => r.recipeId === recipeId);
  if (!ref) {
    return 0;
  }
  const scale = ref.recipeScale ?? 1;
  return roundQuantity((ref.recipeQuantity || 0) * scale);
}

/**
 * Returns a copy of the item with the recipe's share set to `amount`. The item's total changes by
 * the difference, so any extra amount typed in by hand is kept. A share of 0 keeps the reference
 * (the recipe stays linked to the list and can be raised again later).
 */
export function withRecipeShare(item: ShoppingListItemOut, recipeId: string, amount: number): ShoppingListItemOut {
  const target = Math.max(0, Number.isFinite(amount) ? amount : 0);
  const previous = recipeShare(item, recipeId);

  const recipeReferences = (item.recipeReferences || []).map((ref) => {
    if (ref.recipeId !== recipeId) {
      return ref;
    }
    // keep the scale so removing the recipe from the list later takes away exactly this share
    const scale = ref.recipeScale ? ref.recipeScale : 1;
    return { ...ref, recipeScale: scale, recipeQuantity: target / scale };
  });

  return {
    ...item,
    quantity: roundQuantity(Math.max(0, (item.quantity || 0) - previous + target)),
    recipeReferences,
  };
}

/** Shows at most two decimals, without trailing zeros */
export function formatShare(n: number): string {
  return (Math.round(n * 100) / 100).toString();
}

export function unitLabel(item: ShoppingListItemOut): string {
  const unit = item.unit;
  if (!unit) {
    return "";
  }
  return unit.useAbbreviation && unit.abbreviation ? unit.abbreviation : unit.name;
}
