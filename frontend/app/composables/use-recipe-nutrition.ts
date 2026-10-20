import { HouseholdPlannerAPI } from "~/lib/api/user/household-planner";
import { useRequests } from "~/composables/api/api-client";

// Fork: per-portion nutrition comes from the household planner facts (numeric, sourced per ingredient).
export const NUTRIENTS = ["calories", "protein", "carbohydrate", "fat"] as const;
export type Nutrient = typeof NUTRIENTS[number];
export type PortionNutrition = Record<Nutrient, number | null>;
export type NutritionFilter = Record<Nutrient, [number, number]>;

/** Slider bounds; a range spanning the full bounds does not filter. */
export const NUTRITION_LIMITS: NutritionFilter = {
  calories: [0, 1200],
  protein: [0, 100],
  carbohydrate: [0, 150],
  fat: [0, 60],
};

export function defaultNutritionFilter(): NutritionFilter {
  return {
    calories: [...NUTRITION_LIMITS.calories],
    protein: [...NUTRITION_LIMITS.protein],
    carbohydrate: [...NUTRITION_LIMITS.carbohydrate],
    fat: [...NUTRITION_LIMITS.fat],
  };
}

function isActive(filter: NutritionFilter, key: Nutrient) {
  const [min, max] = filter[key];
  const [lo, hi] = NUTRITION_LIMITS[key];
  return min > lo || max < hi;
}

export function nutritionFilterActive(filter: NutritionFilter) {
  return NUTRIENTS.some(key => isActive(filter, key));
}

/** The upper bound is open: "1200" on the slider means 1200 or more. Unknown values never match an active range. */
export function matchesNutrition(value: PortionNutrition | undefined, filter: NutritionFilter) {
  return NUTRIENTS.every((key) => {
    if (!isActive(filter, key)) return true;
    const amount = value?.[key];
    if (amount == null) return false;
    const [min, max] = filter[key];
    return amount >= min && (max >= NUTRITION_LIMITS[key][1] || amount <= max);
  });
}

const NO_RECIPE = "00000000-0000-0000-0000-000000000000";

/** Mealie query filter restricting a recipe search to the given ids (none matching → no results). */
export function recipeIdFilter(ids: string[]) {
  const values = (ids.length ? ids : [NO_RECIPE]).map(id => `"${id}"`).join(", ");
  return `id IN [${values}]`;
}

/** URL form "calories:200-700,protein:30-100"; only active ranges are written. */
export function serializeNutritionFilter(filter: NutritionFilter) {
  return NUTRIENTS.filter(key => isActive(filter, key)).map(key => `${key}:${filter[key][0]}-${filter[key][1]}`).join(",");
}

export function parseNutritionFilter(raw: string | null | undefined): NutritionFilter {
  const filter = defaultNutritionFilter();
  for (const part of (raw || "").split(",")) {
    const match = /^(\w+):(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$/.exec(part.trim());
    if (!match || !(NUTRIENTS as readonly string[]).includes(match[1]!)) continue;
    const key = match[1] as Nutrient;
    const [lo, hi] = NUTRITION_LIMITS[key];
    const min = Math.max(lo, Math.min(hi, Number(match[2])));
    const max = Math.max(min, Math.min(hi, Number(match[3])));
    filter[key] = [min, max];
  }
  return filter;
}

const byId = ref<Record<string, PortionNutrition> | null>(null);
let pending: Promise<void> | null = null;

/** Shared, lazily loaded per-portion nutrition of the household's recipes (empty for guests). */
export function useRecipeNutrition() {
  const requests = useRequests();

  async function load(force = false) {
    if (byId.value && !force) return;
    if (!pending) {
      pending = new HouseholdPlannerAPI(requests).state()
        .then((state) => {
          const result: Record<string, PortionNutrition> = {};
          for (const facts of Object.values(state.state.facts || {})) {
            const p = facts.per_serving;
            result[facts.recipe_id] = {
              calories: p.calories ?? null,
              protein: p.protein ?? null,
              carbohydrate: p.carbohydrate ?? null,
              fat: p.fat ?? null,
            };
          }
          byId.value = result;
        })
        .catch(() => {
          byId.value = {};
        })
        .finally(() => {
          pending = null;
        });
    }
    await pending;
  }

  function matchingIds(filter: NutritionFilter) {
    return Object.entries(byId.value || {}).filter(([, value]) => matchesNutrition(value, filter)).map(([id]) => id);
  }

  return { byId, load, matchingIds };
}
