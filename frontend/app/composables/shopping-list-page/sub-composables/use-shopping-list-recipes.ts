import type { ShoppingListOut } from "~/lib/api/types/household";
import { useUserApi } from "~/composables/api";

/** Portions a recipe reference stands for (reference quantity is in recipe multiples). Null without a yield. */
export function portionsFor(recipeQuantity: number | null | undefined, servings: number | null | undefined) {
  if (!servings || servings <= 0) return null;
  return Math.round((recipeQuantity || 0) * servings * 10) / 10;
}

/** One click changes the list by one portion when the recipe has a yield, otherwise by one whole recipe. */
function stepFor(servings: number | null | undefined) {
  return servings && servings > 0 ? 1 / servings : 1;
}

/**
 * Composable for managing shopping list recipe references
 */
export function useShoppingListRecipes(
  shoppingList: Ref<ShoppingListOut | null>,
  loadingCounter: Ref<number>,
  recipeReferenceLoading: Ref<boolean>,
  refresh: () => void,
) {
  const userApi = useUserApi();

  async function addRecipeReferenceToList(recipeId: string, servings?: number | null) {
    if (!shoppingList.value || recipeReferenceLoading.value) {
      return;
    }

    loadingCounter.value += 1;
    recipeReferenceLoading.value = true;
    const { data } = await userApi.shopping.lists.addRecipes(shoppingList.value.id, [
      { recipeId, recipeIncrementQuantity: stepFor(servings) },
    ]);
    recipeReferenceLoading.value = false;
    loadingCounter.value -= 1;

    if (data) {
      refresh();
    }
  }

  async function removeRecipeReferenceToList(recipeId: string, servings?: number | null) {
    if (!shoppingList.value || recipeReferenceLoading.value) {
      return;
    }

    loadingCounter.value += 1;
    recipeReferenceLoading.value = true;
    const { data } = await userApi.shopping.lists.removeRecipe(shoppingList.value.id, recipeId, stepFor(servings));
    recipeReferenceLoading.value = false;
    loadingCounter.value -= 1;

    if (data) {
      refresh();
    }
  }

  return {
    addRecipeReferenceToList,
    removeRecipeReferenceToList,
  };
}
