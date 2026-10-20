<template>
  <!-- Fork: kcal and macros per portion on recipe cards; wraps between values, never inside one -->
  <div
    v-if="value"
    class="fork-card-nutrition"
    :title="`${$t('recipe.per-serving')}: ${format(value.calories)} kcal, ${format(value.protein)} g ${$t('recipe.protein-content')}, ${format(value.carbohydrate)} g ${$t('recipe.carbohydrate-content')}, ${format(value.fat)} g ${$t('recipe.fat-content')}`"
  >
    <strong>{{ format(value.calories) }} kcal</strong>
    <span>E {{ format(value.protein) }} g</span>
    <span>KH {{ format(value.carbohydrate) }} g</span>
    <span>F {{ format(value.fat) }} g</span>
  </div>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useRecipeNutrition } from "~/composables/use-recipe-nutrition";

const props = defineProps<{ recipeId: string }>();

const { isOwnGroup } = useLoggedInState();
const { byId, load } = useRecipeNutrition();
const value = computed(() => byId.value?.[props.recipeId]);
const format = (n: number | null) => (n == null ? "—" : Math.round(n).toString());

onMounted(() => {
  if (isOwnGroup.value) load();
});
</script>

<style scoped>
.fork-card-nutrition {
  display: flex;
  flex-wrap: wrap;
  gap: 0 10px;
  white-space: nowrap;
  font-size: 0.8rem;
  line-height: 1.4;
  color: rgb(var(--v-theme-on-surface));
}

.fork-card-nutrition span {
  opacity: 0.8;
}
</style>
