<template>
  <!-- Fork: per-portion kcal and macro ranges -->
  <v-menu
    v-model="menu"
    offset-y
    bottom
    nudge-bottom="3"
    :close-on-content-click="false"
  >
    <template #activator="{ props: menuProps }">
      <v-badge
        :model-value="activeCount > 0"
        size="small"
        color="primary"
        :content="activeCount"
      >
        <v-btn
          size="small"
          variant="tonal"
          rounded="pill"
          class="fork-filter-btn"
          :color="activeCount > 0 ? 'primary' : undefined"
          v-bind="menuProps"
        >
          <v-icon start>
            {{ $globals.icons.potSteam }}
          </v-icon>
          {{ $t('recipe.nutrition') }}
        </v-btn>
      </v-badge>
    </template>
    <v-card width="400" max-width="calc(100vw - 32px)">
      <v-card-text>
        <p class="text-medium-emphasis text-body-2 mb-4">
          {{ $t('recipe-finder.nutrition-per-portion') }}
        </p>
        <div v-for="item in sliders" :key="item.key" class="mb-2">
          <div class="d-flex justify-space-between text-body-2">
            <span>{{ item.label }}</span>
            <span class="text-medium-emphasis">{{ rangeText(item.key) }}</span>
          </div>
          <v-range-slider
            v-model="model[item.key]"
            :min="NUTRITION_LIMITS[item.key][0]"
            :max="NUTRITION_LIMITS[item.key][1]"
            :step="item.step"
            color="primary"
            hide-details
            strict
            :aria-label="item.label"
          />
        </div>
        <div class="d-flex justify-end">
          <v-btn variant="text" color="primary" :disabled="activeCount === 0" @click="reset">
            {{ $t('general.reset') }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import {
  NUTRIENTS,
  NUTRITION_LIMITS,
  defaultNutritionFilter,
  type Nutrient,
  type NutritionFilter,
} from "~/composables/use-recipe-nutrition";

const model = defineModel<NutritionFilter>({ required: true });
const i18n = useI18n();
const menu = ref(false);

const sliders = computed<{ key: Nutrient; label: string; step: number }[]>(() => [
  { key: "calories", label: i18n.t("recipe.calories"), step: 50 },
  { key: "protein", label: i18n.t("recipe.protein-content"), step: 5 },
  { key: "carbohydrate", label: i18n.t("recipe.carbohydrate-content"), step: 5 },
  { key: "fat", label: i18n.t("recipe.fat-content"), step: 5 },
]);

const activeCount = computed(() => NUTRIENTS.filter((key) => {
  const [min, max] = model.value[key];
  return min > NUTRITION_LIMITS[key][0] || max < NUTRITION_LIMITS[key][1];
}).length);

function rangeText(key: Nutrient) {
  const unit = key === "calories" ? "kcal" : "g";
  const [min, max] = model.value[key];
  const upper = max >= NUTRITION_LIMITS[key][1] ? `${max}+` : `${max}`;
  return `${min}–${upper} ${unit}`;
}

function reset() {
  model.value = defaultNutritionFilter();
}
</script>
