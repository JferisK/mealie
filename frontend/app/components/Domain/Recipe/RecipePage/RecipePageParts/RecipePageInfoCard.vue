<template>
  <!--
    Fork: compact recipe header. Title, rating, description and one wrapping
    meta row (times, yield, last made, actions) so ingredients start within the
    first screen on a phone instead of after a stack of centred blocks.
  -->
  <div class="recipe-head" :class="{ 'recipe-head--side': !landscape && recipe.image }">
    <RecipePageInfoCardImage
      v-if="landscape && recipe.image"
      :recipe="recipe"
      class="recipe-head__image"
    />
    <div class="recipe-head__body">
      <h1 class="recipe-head__title">
        {{ recipe.name }}
      </h1>
      <RecipeRating
        :key="recipe.slug"
        :model-value="recipe.rating"
        :recipe-id="recipe.id"
        :slug="recipe.slug"
        small
        class="recipe-head__rating"
      />
      <SafeMarkdown v-if="recipe.description" :source="recipe.description" class="recipe-head__desc" />
      <div class="recipe-head__meta">
        <RecipeTimeCard
          inline
          :prep-time="recipe.prepTime"
          :total-time="recipe.totalTime"
          :perform-time="recipe.performTime"
        />
        <!-- Fork: no yield row; portions are set with the scaler below -->
      </div>
      <!-- Fork: kcal and macros per portion right under the times -->
      <section v-if="perPortion.length" class="recipe-head__nutrition" :aria-label="$t('recipe.nutrition')">
        <div class="recipe-head__nutrition-title">
          {{ $t('recipe.per-serving') }}
        </div>
        <div class="recipe-head__nutrients">
          <div v-for="item in perPortion" :key="item.label" class="recipe-head__nutrient">
            <span class="recipe-head__nutrient-value">{{ item.value }}</span>
            <span class="recipe-head__nutrient-label">{{ item.label }}</span>
          </div>
        </div>
      </section>
      <div class="recipe-head__actions">
        <RecipeLastMade
          v-if="isOwnGroup"
          :recipe="recipe"
          compact
        />
        <slot name="actions" />
      </div>
    </div>
    <RecipePageInfoCardImage
      v-if="!landscape && recipe.image"
      :recipe="recipe"
      max-width="50%"
      class="recipe-head__image recipe-head__image--side"
    />
  </div>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import RecipeRating from "~/components/Domain/Recipe/RecipeRating.vue";
import RecipeLastMade from "~/components/Domain/Recipe/RecipeLastMade.vue";
import RecipeTimeCard from "~/components/Domain/Recipe/RecipeTimeCard.vue";
import RecipePageInfoCardImage from "~/components/Domain/Recipe/RecipePage/RecipePageParts/RecipePageInfoCardImage.vue";
import type { Recipe } from "~/lib/api/types/recipe";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";

interface Props {
  recipe: NoUndefinedField<Recipe>;
  recipeScale?: number;
  landscape: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  recipeScale: 1,
});

const i18n = useI18n();
const perPortion = computed(() => {
  const n = props.recipe.nutrition;
  const number = (v: string | null | undefined) => {
    const parsed = v == null ? Number.NaN : Number.parseFloat(String(v).replace(",", "."));
    return Number.isFinite(parsed) ? Math.round(parsed) : null;
  };
  const items = [
    { label: "kcal", value: number(n?.calories) },
    { label: i18n.t("recipe.protein-content"), value: number(n?.proteinContent), unit: "g" },
    { label: i18n.t("recipe.carbohydrate-content"), value: number(n?.carbohydrateContent), unit: "g" },
    { label: i18n.t("recipe.fat-content"), value: number(n?.fatContent), unit: "g" },
  ];
  if (items[0]!.value === null) return [];
  return items.filter(i => i.value !== null).map(i => ({ label: i.label, value: `${i.value}${i.unit ? ` ${i.unit}` : ""}` }));
});

const { isOwnGroup } = useLoggedInState();
</script>

<style scoped>
.recipe-head {
  display: flex;
  flex-direction: column;
}

.recipe-head--side {
  flex-direction: row;
  align-items: stretch;
}

.recipe-head__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 0;
  min-width: 0;
  padding: 16px 16px 4px;
}

.recipe-head--side .recipe-head__body {
  justify-content: center;
  padding: 24px;
}

.recipe-head__image--side {
  flex: 0 0 50%;
  border-radius: 0 var(--fork-radius-card) 0 0;
}

.recipe-head__nutrition {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.recipe-head__nutrition-title {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.85;
}

.recipe-head__nutrients {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  max-width: 520px;
}

@media (max-width: 480px) {
  .recipe-head__nutrients {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.recipe-head__nutrient {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 4px;
  border-radius: 10px;
  border: 1px solid rgba(var(--v-theme-primary), 0.55);
  background: rgba(var(--v-theme-primary), 0.18);
  text-align: center;
}

.recipe-head__nutrient-value {
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.2;
  color: rgb(var(--v-theme-on-surface));
  white-space: nowrap;
}

.recipe-head__nutrient-label {
  font-size: 0.8rem;
  line-height: 1.2;
  color: rgb(var(--v-theme-on-surface));
}

.recipe-head__title {
  font-size: clamp(1.4rem, 1.2rem + 0.9vw, 2rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.recipe-head__rating {
  margin-left: -6px;
}

.recipe-head__desc {
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--fork-ink-soft);
}

.recipe-head__desc :deep(p) {
  margin: 0;
}

.recipe-head__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 16px;
}

.recipe-head__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

@media (max-width: 959.98px) {
  .recipe-head--side {
    flex-direction: column-reverse;
  }

  .recipe-head__image--side {
    flex-basis: auto;
    max-width: 100% !important;
    border-radius: 0;
  }

  .recipe-head--side .recipe-head__body {
    padding: 16px 16px 4px;
  }
}
</style>
