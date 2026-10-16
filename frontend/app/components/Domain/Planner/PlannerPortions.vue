<template>
  <v-container class="planner-shell">
    <RecipeDialogAddToShoppingList v-model="shoppingDialog" :recipes="shoppingRecipes" :shopping-lists="shoppingLists" />
    <div v-if="tab !== 'cook'" class="d-flex justify-end">
      <v-btn :icon="mdiRefresh" variant="text" :aria-label="t('refresh')" :loading="busy" @click="run(refreshAll)" />
    </div>
    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
      role="alert"
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>
    <v-progress-linear v-if="busy && !data" indeterminate :aria-label="t('loading')" />
    <template v-if="data">
      <div v-if="tab === 'cook'" class="week-navigation">
        <v-btn :icon="mdiChevronLeft" variant="text" :aria-label="t('previous')" :disabled="busy" @click="shiftWeek(-7)" />
        <strong>{{ weekLabel }}</strong>
        <v-btn :icon="mdiChevronRight" variant="text" :aria-label="t('next')" :disabled="busy" @click="shiftWeek(7)" />
        <v-btn :icon="mdiRefresh" variant="text" :aria-label="t('refresh')" :loading="busy" @click="run(refreshAll)" />
      </div>
      <section v-if="tab === 'freezer'">
        <div class="stock-summary">
          <div><strong>{{ number(stockTotal) }}</strong><span>{{ t('portionsFrozen') }}</span></div><div><strong>{{ number(stockAvailable) }}</strong><span>{{ t('available') }}</span></div><v-btn :prepend-icon="mdiPlus" color="primary" :disabled="busy" @click="freezeDialog = true">
            {{ t('addStock') }}
          </v-btn>
        </div>
        <v-text-field
          v-model="stockSearch"
          :label="t('searchStock')"
          variant="outlined"
          density="comfortable"
          hide-details
          clearable
          @click:clear="stockSearch = ''"
        />
        <v-checkbox v-model="showEmpty" :label="t('showEmpty')" hide-details density="compact" class="mb-3" />
        <div class="stock-grid">
          <article v-for="batch in filteredBatches" :key="batch.id" class="stock-card">
            <div class="stock-card-heading">
              <v-icon :icon="mdiSnowflake" /><div><h3>{{ batch.facts.name }}</h3><p>{{ batch.location || t('noLocation') }} · {{ shortDate(batch.frozen_on) }}</p></div>
            </div>
            <div class="stock-quantities">
              <strong>{{ number(batch.remaining) }} <small>{{ t('portions') }}</small></strong><span>{{ number(available(batch.id!)) }} {{ t('available') }} · {{ number(batch.remaining - available(batch.id!)) }} {{ t('reserved') }}</span>
            </div>
            <div class="stock-card-footer">
              <details v-if="batch.facts.reheating_instructions">
                <summary>{{ t('reheating') }}</summary><p>{{ batch.facts.reheating_instructions }}</p>
              </details><v-btn variant="tonal" :disabled="busy || available(batch.id!) <= 0" @click="askWithdraw(batch.id!)">
                {{ t('withdraw') }}
              </v-btn>
            </div>
          </article>
        </div>
        <p v-if="!filteredBatches.length" class="empty-state">
          {{ t(batches.length ? 'noMatches' : 'emptyFreezer') }}
        </p>
      </section>
      <section v-if="tab === 'cook'">
        <div class="native-shopping-actions">
          <v-btn color="primary" :prepend-icon="mdiCartOutline" :disabled="busy || !currentPlan || !summary?.cooking.length" @click="prepareShopping">
            {{ t('addFreshToList') }}
          </v-btn>
          <v-btn variant="text" to="/shopping-lists">
            {{ $t('shopping-list.shopping-lists') }}
          </v-btn>
        </div>
        <p class="section-hint">
          {{ t('nativeShoppingHint') }}
        </p>
        <p class="section-hint">
          {{ t('cookHint') }}
        </p>
        <div class="cooking-list">
          <article v-for="(dish, index) in summary?.cooking || []" :key="dish.recipe_id" class="cook-card">
            <span class="cook-number">{{ index + 1 }}</span><div><h3>{{ dish.name }}</h3><p>{{ number(dish.servings) }} {{ t('portions') }}</p></div><v-btn variant="tonal" :disabled="busy" @click="freezeRecipe = dish.recipe_id; freezeServings = dish.servings; freezeDialog = true">
              {{ t('freeze') }}
            </v-btn>
          </article>
        </div>
        <p v-if="!summary?.cooking.length" class="empty-state">
          {{ t('noCooking') }}
        </p>
      </section>
      <PlannerPersonalPanel
        v-if="tab === 'goals' && personal"
        :personal="personal"
        :busy="busy"
        :week-average="weekAverage"
        @save-profile="p => run(() => privateMutate('/profile', p, 'put'))"
        @add-weight="addWeight"
        @adopt="adoptGoal"
        @manual="adoptManual"
      />
    </template>
    <v-dialog v-model="freezeDialog" scrollable class="planner-dialog" max-width="500">
      <v-card :title="t('freeze')" rounded="xl">
        <v-card-text>
          <v-select v-model="freezeRecipe" :items="recipes" item-title="name" item-value="recipe_id" :label="t('recipe')" />
          <v-number-input
            v-model="freezeServings"
            :precision="2"
            inputmode="decimal"
            :min="0.1"
            :step="0.5"
            :label="t('portions')"
          />
          <v-text-field v-model="freezeDate" type="date" :label="t('frozenOn')" />
          <v-text-field v-model="freezeLocation" :label="t('location')" />
        </v-card-text><v-card-actions>
          <v-btn @click="freezeDialog = false">
            {{ t('close') }}
          </v-btn><v-spacer /><v-btn color="primary" :disabled="!freezeRecipe || !freezeServings || freezeServings <= 0 || busy" @click="freeze">
            {{ t('save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog :model-value="!!withdrawBatch" class="planner-dialog" max-width="460" @update:model-value="value => { if (!value) withdrawBatch = null; }">
      <v-card :title="t('withdraw')">
        <v-card-text>
          <h3 class="mb-4">
            {{ selectedBatch?.facts.name }}
          </h3><p class="mb-4">
            {{ t('withdrawHint') }}
          </p><v-number-input
            v-model="withdrawQuantity"
            :precision="2"
            inputmode="decimal"
            :min="0.1"
            :max="withdrawBatch ? available(withdrawBatch) : 0"
            :step="0.5"
            :label="t('portions')"
          />
        </v-card-text><v-card-actions>
          <v-btn :disabled="busy" @click="withdrawBatch = null">
            {{ t('close') }}
          </v-btn><v-spacer /><v-btn color="primary" :disabled="busy || !withdrawQuantity || withdrawQuantity <= 0 || withdrawQuantity > available(withdrawBatch!)" @click="withdraw">
            {{ t('confirm') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { mdiSnowflake, mdiCartOutline, mdiRefresh, mdiChevronLeft, mdiChevronRight, mdiPlus } from "@mdi/js";
import RecipeDialogAddToShoppingList, { type RecipeWithScale } from "~/components/Domain/Recipe/RecipeDialogAddToShoppingList.vue";
import { useAddToShoppingListDialog } from "~/composables/shopping-list-page/use-add-to-shopping-list-dialog";
import { useUserApi } from "~/composables/api";
import { addDays, format, startOfWeek, parseISO } from "date-fns";
import type { BatchIn, GoalsIn, ProfileIn } from "~/lib/api/types/household-planner";
import { useHouseholdPlanner, type PlannerSummary } from "~/composables/use-household-planner";
import PlannerPersonalPanel from "~/components/Domain/Planner/PlannerPersonalPanel.vue";

const i18n = useI18n();
const auth = useMealieAuth();
const t = (key: string) => i18n.t(`household-planner.${key}`);
const { api, data, personal, busy, error, run, refresh, mutate, privateMutate } = useHouseholdPlanner();
const route = useRoute();
const pageProps = defineProps<{ section?: "ideas" | "week" | "cook" | "freezer" | "goals" }>();
const tab = computed(() => pageProps.section ?? (["freezer", "goals"].includes(String(route.query.section)) ? String(route.query.section) : "cook"));
const nativeApi = useUserApi();
const { shoppingLists, open: shoppingDialog, getShoppingLists } = useAddToShoppingListDialog();
const shoppingRecipes = ref<RecipeWithScale[]>([]);
function prepareShopping() {
  run(async () => {
    await loadSummary();
    const recipes: RecipeWithScale[] = [];
    for (const dish of summary.value?.cooking || []) {
      if (dish.servings <= 0) continue;
      const slug = data.value?.state.facts?.[dish.recipe_id]?.slug;
      if (!slug) throw new Error(t("shoppingRecipeMissing"));
      const response = await nativeApi.recipes.getOne(slug);
      if (response.error || !response.data) throw new Error(t("shoppingRecipeMissing"));
      const recipe = response.data;
      if (!recipe.recipeServings || recipe.recipeServings <= 0) throw new Error(`${recipe.name}: ${t("shoppingYieldMissing")}`);
      recipes.push({ ...recipe, scale: dish.servings / recipe.recipeServings });
    }
    if (!recipes.length) return;
    shoppingRecipes.value = recipes;
    await getShoppingLists();
    shoppingDialog.value = true;
  });
}
const stockSearch = ref("");
const showEmpty = ref(false);
const withdrawBatch = ref<string | null>(null);
const withdrawQuantity = ref(1);
const week = ref(format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd"));
const days = computed(() => Array.from({ length: 7 }, (_, i) => format(addDays(parseISO(week.value), i), "yyyy-MM-dd")));
const shortDate = (day: string) => new Intl.DateTimeFormat(i18n.locale.value, { day: "numeric", month: "short" }).format(parseISO(day));
const weekLabel = computed(() => `${shortDate(week.value)} – ${shortDate(days.value[6]!)}`);
const currentPlan = computed(() => Object.values(data.value?.state.plans || {}).find(p => p.start === week.value));
const summary = ref<PlannerSummary | null>(null);
const recipes = computed(() => Object.values(data.value?.state.facts || {}));
const batches = computed(() => Object.values(data.value?.state.batches || {}).sort((a, b) => a.frozen_on.localeCompare(b.frozen_on)));
const filteredBatches = computed(() => batches.value.filter(b => (showEmpty.value || b.remaining > 0) && `${b.facts.name} ${b.location}`.toLocaleLowerCase().includes((stockSearch.value || "").toLocaleLowerCase())));
const stockTotal = computed(() => batches.value.reduce((s, b) => s + b.remaining, 0));
const stockAvailable = computed(() => batches.value.reduce((s, b) => s + available(b.id!), 0));
const selectedBatch = computed(() => batches.value.find(b => b.id === withdrawBatch.value));
const freezeDialog = ref(false);
const freezeRecipe = ref(""); const freezeServings = ref(1); const freezeLocation = ref(""); const freezeDate = ref(format(new Date(), "yyyy-MM-dd"));
const number = (v: number | null | undefined) => v == null ? "—" : new Intl.NumberFormat(i18n.locale.value, { maximumFractionDigits: 1 }).format(v);
function available(id: string) {
  const reserved = Object.values(data.value?.state.plans || {}).flatMap(p => (p.entries || []).filter(e => e.batch_id === id && !p.consumed?.includes(e.id!))).reduce((s, e) => s + e.servings, 0);
  return (data.value?.state.batches?.[id]?.remaining || 0) - reserved;
}
async function loadSummary() { summary.value = currentPlan.value?.id ? await api.read<PlannerSummary>(`/plans/${currentPlan.value.id}/summary`) : null; }
function shiftWeek(n: number) {
  week.value = format(addDays(parseISO(week.value), n), "yyyy-MM-dd");
  summary.value = null;
  run(loadSummary);
}
async function refreshAll() { await refresh(); await loadSummary(); }
function askWithdraw(id: string) { withdrawQuantity.value = Math.min(1, available(id)); withdrawBatch.value = id; }
function withdraw() {
  if (!withdrawBatch.value || !withdrawQuantity.value) return;
  run(async () => { await mutate("/movements", { id: crypto.randomUUID(), batch_id: withdrawBatch.value, kind: "withdraw", servings: withdrawQuantity.value }); withdrawBatch.value = null; });
}
function freeze() { const payload: BatchIn = { id: crypto.randomUUID(), recipe_id: freezeRecipe.value, servings: freezeServings.value, frozen_on: freezeDate.value, location: freezeLocation.value }; run(async () => { await mutate("/batches", payload); freezeDialog.value = false; }); }
// Average planned intake of the signed-in person over days that have meals this week.
const weekAverage = computed(() => {
  const self = auth.user.value?.id;
  const perDay = new Map<string, { calories: number; protein: number }>();
  for (const e of currentPlan.value?.entries || []) {
    if (e.user_id !== self) continue;
    const facts = e.batch_id ? data.value?.state.batches?.[e.batch_id]?.facts : currentPlan.value?.recipe_snapshots?.[e.recipe_id] || data.value?.state.facts?.[e.recipe_id];
    const day = perDay.get(e.day) || { calories: 0, protein: 0 };
    day.calories += (facts?.per_serving.calories || 0) * e.servings;
    day.protein += (facts?.per_serving.protein || 0) * e.servings;
    perDay.set(e.day, day);
  }
  if (!perDay.size) return null;
  const all = [...perDay.values()];
  return { calories: all.reduce((s, d) => s + d.calories, 0) / all.length, protein: all.reduce((s, d) => s + d.protein, 0) / all.length };
});
function addWeight(kg: number) {
  const now = new Date();
  run(() => privateMutate("/health", {
    observations: [{ id: `manual:${format(now, "yyyy-MM-dd")}`, kind: "weight_kg", value: kg, at: now.toISOString(), source: "manual" }],
    deleted_ids: [],
  }));
}
async function confirmLatest() {
  const latest = personal.value?.state.revisions?.at(-1);
  if (latest?.id) await privateMutate(`/goals/${latest.id}/confirm`);
}
function adoptGoal(profile: ProfileIn) {
  run(async () => {
    await privateMutate("/profile", profile, "put");
    await privateMutate("/goals/propose");
    await confirmLatest();
  });
}
function adoptManual(goals: GoalsIn) {
  run(async () => {
    await privateMutate("/goals/manual", goals);
    await confirmLatest();
  });
}
onMounted(() => run(refreshAll));
</script>

<style scoped>
.planner-shell {
  --line: rgba(var(--v-theme-on-surface), 0.1);
  max-width: 1120px;
  padding: 0 0 calc(24px + env(safe-area-inset-bottom));
}
.planner-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.eyebrow {
  color: rgb(var(--v-theme-primary));
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}
h1 {
  font-size: 1.75rem;
  line-height: 1.2;
  letter-spacing: -0.04em;
  margin-top: 3px;
}
h2 {
  font-size: 1.15rem;
}
h3 {
  font-size: 1rem;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
button {
  touch-action: manipulation;
}
.person-switch button,
.day-strip button {
  border: 0;
  background: transparent;
  font: inherit;
  cursor: pointer;
}
button:focus-visible,
a:focus-visible,
summary:focus-visible,
input:focus-visible {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: 3px;
}
.week-navigation {
  display: grid;
  grid-template-columns: 44px 1fr 44px 44px;
  align-items: center;
  text-align: center;
  margin: 0 -6px 10px;
}
.week-navigation strong {
  font-size: 0.95rem;
}
.person-switch {
  display: flex;
  gap: 6px;
  padding: 4px;
  background: rgba(var(--v-theme-on-surface), 0.045);
  border-radius: 14px;
  margin-bottom: 16px;
  overflow-x: auto;
}
.person-switch button {
  flex: 1;
  min-height: 44px;
  padding: 8px 12px;
  border-radius: 11px;
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
}
.person-switch button[aria-pressed="true"] {
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}
.day-strip {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  padding: 3px 0;
}
.day-strip button {
  flex: 1 0 42px;
  min-height: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  border-radius: 15px;
}
.day-strip span {
  font-size: 0.7rem;
  opacity: 0.75;
}
.day-strip strong {
  font-size: 1.05rem;
}
.day-strip .is-today strong {
  text-decoration: underline;
  text-underline-offset: 4px;
}
.day-strip button[aria-pressed="true"] {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}
.day-strip i {
  width: 4px;
  height: 4px;
  margin-top: 2px;
  border-radius: 50%;
}
.day-strip i.filled {
  background: currentColor;
}
.day-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin: 16px 0 10px;
}
.day-actions h2 {
  flex: 1;
}
.day-actions h2 span {
  display: block;
  font-size: 0.75rem;
  opacity: 0.6;
  font-weight: 400;
}
.week-overview {
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 16px;
}
.week-overview button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 52px;
  padding: 10px 12px;
  text-align: left;
  font-size: 0.8rem;
  border-bottom: 1px solid var(--line);
}
.week-overview button span {
  flex: 1;
}
.week-overview button:last-child {
  border: 0;
}
.daily-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(var(--v-theme-primary), 0.065);
  margin-bottom: 18px;
}
.daily-summary div + div {
  padding-left: 18px;
  border-left: 1px solid var(--line);
}
.daily-summary span {
  display: block;
  font-size: 0.75rem;
  opacity: 0.72;
}
.daily-summary strong {
  font-size: 1.55rem;
  letter-spacing: -0.04em;
}
.daily-summary small {
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0;
}
.daily-summary p {
  grid-column: 1 / -1;
  font-size: 0.7rem;
  opacity: 0.65;
}
.meal-list {
  display: grid;
  gap: 12px;
}
.meal-card {
  border: 1px solid var(--line);
  border-radius: 18px;
  overflow: hidden;
  background: rgb(var(--v-theme-surface));
}
.meal-main {
  display: flex;
  gap: 14px;
  padding: 14px 14px 10px;
  color: inherit;
  text-decoration: none;
  min-height: 112px;
}
.meal-main img,
.meal-placeholder {
  width: 80px;
  height: 88px;
  border-radius: 12px;
  object-fit: cover;
  flex-shrink: 0;
}
.meal-placeholder {
  display: grid;
  place-items: center;
  background: rgba(var(--v-theme-primary), 0.08);
  color: rgb(var(--v-theme-primary));
}
.meal-copy {
  min-width: 0;
}
.meal-label {
  font-size: 0.65rem;
  font-weight: 600;
  color: rgb(var(--v-theme-primary));
}
.meal-copy h3 {
  margin: 5px 0 8px;
}
.meal-copy p {
  font-size: 0.75rem;
}
.meal-copy p span {
  opacity: 0.7;
}
.meal-footer {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px 10px;
}
.diet-labels {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.diet-labels span {
  font-size: 0.6rem;
  background: rgba(var(--v-theme-on-surface), 0.045);
  padding: 4px 7px;
  border-radius: 6px;
}
.recorded {
  background: rgba(var(--v-theme-on-surface), 0.025);
}
.recorded-label {
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 44px;
}
:deep(.v-btn) {
  min-height: 44px;
  letter-spacing: 0;
}
:deep(.v-btn--icon) {
  min-width: 44px;
  width: 44px;
  height: 44px;
}
.draft-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}
.draft-actions > * {
  flex: 1;
}
.section-hint {
  font-size: 0.8rem;
  color: rgba(var(--v-theme-on-surface), 0.65);
  margin: 14px 0 18px;
  line-height: 1.5;
}
.empty-state {
  text-align: center;
  padding: 28px 16px;
  color: rgba(var(--v-theme-on-surface), 0.65);
}
.empty-state h3 {
  margin: 12px 0 6px;
}
.empty-state p {
  font-size: 0.85rem;
}
.stock-summary {
  display: flex;
  align-items: center;
  gap: 20px;
  margin: 20px 0;
}
.stock-summary > div {
  display: flex;
  flex-direction: column;
}
.stock-summary strong {
  font-size: 1.65rem;
  line-height: 1.1;
}
.stock-summary span {
  font-size: 0.7rem;
  opacity: 0.65;
  margin-top: 5px;
}
.stock-summary .v-btn {
  margin-left: auto;
}
.stock-grid {
  display: grid;
  gap: 12px;
}
.stock-card {
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 18px;
}
.stock-card-heading {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.stock-card-heading > .v-icon {
  color: rgb(var(--v-theme-primary));
  padding-top: 3px;
}
.stock-card-heading p {
  font-size: 0.75rem;
  opacity: 0.65;
  margin-top: 4px;
}
.stock-quantities {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 0;
}
.stock-quantities strong {
  font-size: 1.5rem;
}
.stock-quantities small {
  font-size: 0.8rem;
  font-weight: 400;
}
.stock-quantities > span {
  font-size: 0.75rem;
  opacity: 0.7;
}
.stock-card-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 8px;
}
.stock-card-footer details {
  flex: 1;
  min-width: 130px;
}
.stock-card-footer .v-btn {
  margin-left: auto;
}
summary {
  cursor: pointer;
  padding: 12px 0;
  font-size: 0.8rem;
  min-height: 44px;
}
details p {
  font-size: 0.8rem;
  padding: 8px 0;
}
.cooking-list {
  display: grid;
  gap: 12px;
}
.cook-card {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px;
}
.cook-number {
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
  border-radius: 10px;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  font-size: 0.8rem;
  font-weight: 700;
}
.cook-card p {
  font-size: 0.8rem;
  opacity: 0.7;
  margin-top: 4px;
}
.cook-card .v-btn {
  grid-column: 2;
  justify-self: start;
}
@media (min-width: 900px) {
  .planner-shell {
    padding: 24px 28px 48px;
  }
  .person-switch {
    max-width: 480px;
  }
  .meal-list,
  .stock-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .cooking-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    scroll-behavior: auto !important;
  }
}
.native-shopping-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 20px 0 12px;
}
.native-shopping-actions :deep(.v-btn) {
  min-height: 44px;
  height: auto;
  padding-block: 10px;
}
.native-shopping-actions :deep(.v-btn__content) {
  white-space: normal;
}
</style>

<style>
@media (max-width: 599px) {
  .planner-dialog .v-overlay__content {
    align-self: flex-end;
    width: 100% !important;
    max-width: 100% !important;
    max-height: calc(100dvh - 24px) !important;
    margin: 0 !important;
  }
  .planner-dialog .v-card {
    border-radius: 24px 24px 0 0 !important;
    padding-bottom: env(safe-area-inset-bottom);
  }
  .planner-dialog .v-card-title {
    white-space: normal;
  }
  .planner-dialog .v-card-actions {
    min-height: 72px;
    flex-wrap: wrap;
  }
  .planner-dialog .v-btn {
    min-height: 44px;
  }
}
</style>
