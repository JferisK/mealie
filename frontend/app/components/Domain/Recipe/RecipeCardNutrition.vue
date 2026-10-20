<template>
  <!-- Fork: kcal and macros per portion on recipe cards -->
  <div v-if="value" class="fork-card-nutrition" :aria-label="$t('recipe.nutrition')">
    <span class="fork-card-nutrition__kcal">{{ format(value.calories) }} kcal</span>
    <span>{{ format(value.protein) }} g {{ $t('recipe.protein-content') }}</span>
    <span>{{ format(value.carbohydrate) }} g KH</span>
    <span>{{ format(value.fat) }} g {{ $t('recipe.fat-content') }}</span>
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
  gap: 2px 10px;
  font-size: 0.8rem;
  line-height: 1.3;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-card-nutrition__kcal {
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}
</style>
