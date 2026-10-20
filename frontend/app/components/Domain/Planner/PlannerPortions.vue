<template>
  <div class="pp">
    <PlannerShoppingDialog v-if="currentPlan && data" v-model="shoppingDialog" :plan-id="currentPlan.id!" :revision="data.revision" @added="linked" />
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
    <v-alert
      v-if="shoppingDone"
      type="success"
      variant="tonal"
      density="compact"
      class="mb-4"
      closable
      @click:close="shoppingDone = false"
    >
      {{ t('shoppingAdded') }}
    </v-alert>
    <v-progress-linear v-if="busy && !data" indeterminate :aria-label="t('loading')" />
    <template v-if="data">
      <!-- Kochen -->
      <section v-if="tab === 'cook'">
        <div class="pp-toolbar">
          <PlannerWeekNav v-model="week" :disabled="busy" />
          <div class="pp-toolbar__actions">
            <v-btn v-if="currentPlan?.shopping_list_id" color="primary" variant="flat" :prepend-icon="mdiCartOutline" :to="`/shopping-lists/${currentPlan.shopping_list_id}`">
              {{ t('openShopping') }}
            </v-btn>
            <template v-else>
              <v-btn color="primary" variant="flat" :prepend-icon="mdiCartOutline" :disabled="busy || !currentPlan || !summary?.cooking.length" @click="shoppingDialog = true">
                {{ t('createShopping') }}
              </v-btn>
              <v-btn variant="text" color="primary" to="/shopping-lists">
                {{ t('toShopping') }}
              </v-btn>
            </template>
          </div>
        </div>
        <ol v-if="summary?.cooking.length" class="pp-list">
          <li v-for="dish in summary.cooking" :key="dish.recipe_id" class="pp-cook">
            <div class="pp-cook__qty" :aria-label="`${number(dish.servings)} ${t('portions')}`">
              <strong>{{ number(dish.servings) }}</strong>
              <span>{{ t('portionsShort') }}</span>
            </div>
            <div class="pp-cook__body">
              <NuxtLink v-if="recipeSlug(dish.recipe_id)" :to="recipeLink(dish.recipe_id)" class="pp-cook__name">
                {{ dish.name }}
              </NuxtLink>
              <span v-else class="pp-cook__name">{{ dish.name }}</span>
              <span class="pp-cook__meta">{{ cookMeta(dish.recipe_id) }}</span>
            </div>
            <v-btn
              variant="text"
              color="primary"
              :prepend-icon="mdiSnowflake"
              :disabled="busy"
              :aria-label="`${t('freeze')}: ${dish.name}`"
              @click="openFreeze(dish.recipe_id, dish.servings)"
            >
              <span class="pp-hide-xs">{{ t('freezeShort') }}</span>
            </v-btn>
          </li>
        </ol>
        <div v-else-if="!busy" class="fork-empty">
          <v-icon :icon="mdiPotSteamOutline" size="32" />
          <strong>{{ t('noCookingTitle') }}</strong>
          <p>{{ t('noCooking') }}</p>
          <v-btn color="primary" variant="tonal" :to="{ path: '/household/portions', query: { week } }">
            {{ t('weekPlan') }}
          </v-btn>
        </div>
        <p v-if="summary?.cooking.length" class="pp-hint">
          {{ t('nativeShoppingHint') }}
        </p>
      </section>

      <!-- Vorrat -->
      <section v-if="tab === 'freezer'">
        <div class="pp-stats">
          <div class="pp-stat">
            <strong>{{ number(stockTotal) }}</strong>
            <span>{{ t('portionsFrozen') }}</span>
          </div>
          <div class="pp-stat">
            <strong>{{ number(stockAvailable) }}</strong>
            <span>{{ t('available') }}</span>
          </div>
          <v-btn
            color="primary"
            variant="flat"
            :prepend-icon="mdiPlus"
            :disabled="busy"
            class="pp-stats__add"
            @click="openFreeze('', 1)"
          >
            {{ t('addStock') }}
          </v-btn>
        </div>
        <div v-if="batches.length" class="pp-filter">
          <v-text-field
            v-model="stockSearch"
            :prepend-inner-icon="mdiMagnify"
            :label="t('searchStock')"
            variant="outlined"
            density="comfortable"
            hide-details
            clearable
            @click:clear="stockSearch = ''"
          />
          <v-switch
            v-model="showEmpty"
            :label="t('showEmpty')"
            color="primary"
            hide-details
            density="compact"
            inset
          />
        </div>
        <ul v-if="filteredBatches.length" class="pp-list pp-list--grid">
          <li v-for="batch in filteredBatches" :key="batch.id" class="pp-batch" :class="{ 'is-empty': batch.remaining <= 0 }">
            <div class="pp-batch__head">
              <v-icon :icon="mdiSnowflake" class="pp-batch__icon" />
              <div class="pp-batch__title">
                <h3>{{ batch.facts.name }}</h3>
                <p>{{ batch.location || t('noLocation') }} · {{ t('frozenOnShort') }} {{ shortDate(batch.frozen_on) }}</p>
              </div>
              <div class="pp-batch__qty">
                <strong>{{ number(batch.remaining) }}</strong>
                <span>{{ t('portionsShort') }}</span>
              </div>
            </div>
            <div class="pp-batch__foot">
              <span class="pp-batch__avail">
                {{ number(available(batch.id!)) }} {{ t('available') }}<template v-if="batch.remaining - available(batch.id!) > 0"> · {{ number(batch.remaining - available(batch.id!)) }} {{ t('reserved') }}</template>
              </span>
              <v-btn variant="tonal" color="primary" size="small" :disabled="busy || available(batch.id!) <= 0" @click="askWithdraw(batch.id!)">
                {{ t('withdraw') }}
              </v-btn>
            </div>
            <details v-if="batch.facts.reheating_instructions" class="pp-batch__details">
              <summary>{{ t('reheating') }}</summary>
              <p>{{ batch.facts.reheating_instructions }}</p>
            </details>
          </li>
        </ul>
        <div v-else class="fork-empty">
          <v-icon :icon="mdiSnowflake" size="32" />
          <strong>{{ batches.length ? t('noMatches') : t('emptyFreezerTitle') }}</strong>
          <p v-if="!batches.length">
            {{ t('emptyFreezer') }}
          </p>
          <v-btn v-if="!batches.length" color="primary" variant="tonal" :prepend-icon="mdiPlus" @click="openFreeze('', 1)">
            {{ t('addStock') }}
          </v-btn>
        </div>
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

    <PlannerSheet v-model="freezeDialog" :title="t('freeze')" max-width="500">
      <v-select
        v-model="freezeRecipe"
        :items="recipes"
        item-title="name"
        item-value="recipe_id"
        :label="t('recipe')"
        variant="outlined"
      />
      <v-number-input
        v-model="freezeServings"
        :precision="2"
        inputmode="decimal"
        :min="0.1"
        :step="0.5"
        :label="t('portions')"
        variant="outlined"
      />
      <v-text-field v-model="freezeDate" type="date" :label="t('frozenOn')" variant="outlined" />
      <v-text-field v-model="freezeLocation" :label="t('location')" variant="outlined" hide-details />
      <template #actions>
        <v-btn color="primary" variant="flat" :loading="busy" :disabled="!freezeRecipe || !freezeServings || freezeServings <= 0" @click="freeze">
          {{ t('save') }}
        </v-btn>
      </template>
    </PlannerSheet>
    <PlannerSheet
      :model-value="!!withdrawBatch"
      :title="t('withdraw')"
      :subtitle="selectedBatch?.facts.name"
      max-width="460"
      @update:model-value="value => { if (!value) withdrawBatch = null; }"
    >
      <p class="mb-4">
        {{ t('withdrawHint') }}
      </p>
      <v-number-input
        v-model="withdrawQuantity"
        :precision="2"
        inputmode="decimal"
        :min="0.1"
        :max="withdrawBatch ? available(withdrawBatch) : 0"
        :step="0.5"
        :label="t('portions')"
        variant="outlined"
        hide-details
      />
      <template #actions>
        <v-btn color="primary" variant="flat" :loading="busy" :disabled="!withdrawQuantity || withdrawQuantity <= 0 || withdrawQuantity > available(withdrawBatch!)" @click="withdraw">
          {{ t('confirm') }}
        </v-btn>
      </template>
    </PlannerSheet>
  </div>
</template>

<script setup lang="ts">
import { mdiSnowflake, mdiCartOutline, mdiMagnify, mdiPlus, mdiPotSteamOutline } from "@mdi/js";
import { format, startOfWeek, parseISO } from "date-fns";
import type { BatchIn, GoalsIn, ProfileIn, StateOut } from "~/lib/api/types/household-planner";
import { useHouseholdPlanner, type PlannerSummary } from "~/composables/use-household-planner";
import PlannerPersonalPanel from "~/components/Domain/Planner/PlannerPersonalPanel.vue";
import PlannerSheet from "~/components/Domain/Planner/PlannerSheet.vue";
import PlannerShoppingDialog from "~/components/Domain/Planner/PlannerShoppingDialog.vue";
import PlannerWeekNav from "~/components/Domain/Planner/PlannerWeekNav.vue";
import { usePlannerPageRefresh } from "~/composables/use-planner-page";

const i18n = useI18n();
const auth = useMealieAuth();
const t = (key: string) => i18n.t(`household-planner.${key}`);
const { api, data, personal, members, busy, error, run, refresh, mutate, privateMutate } = useHouseholdPlanner();
const route = useRoute();
const pageProps = defineProps<{ section?: "ideas" | "week" | "cook" | "freezer" | "goals" }>();
const tab = computed(() => pageProps.section ?? (["freezer", "goals"].includes(String(route.query.section)) ? String(route.query.section) : "cook"));
const shoppingDialog = ref(false);
const shoppingDone = ref(false);
function linked(state: StateOut) {
  data.value = state;
  shoppingDone.value = true;
}
const stockSearch = ref("");
const showEmpty = ref(false);
const withdrawBatch = ref<string | null>(null);
const withdrawQuantity = ref(1);
const week = ref(format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd"));
const shortDate = (day: string) => new Intl.DateTimeFormat(i18n.locale.value, { day: "numeric", month: "short" }).format(parseISO(day));
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
watch(week, () => {
  shoppingDone.value = false;
  summary.value = null;
  run(loadSummary);
});
const recipeSlug = (recipeId: string) => data.value?.state.facts?.[recipeId]?.slug;
const recipeLink = (recipeId: string) => `/g/${auth.user.value?.groupSlug}/r/${recipeSlug(recipeId)}`;
const weekdayShort = (d: string) => new Intl.DateTimeFormat(i18n.locale.value, { weekday: "short" }).format(parseISO(d));
// "Mo, Mi · Jakob, Sanja": when and for whom a dish is cooked fresh this week.
function cookMeta(recipeId: string) {
  const fresh = (currentPlan.value?.entries || []).filter(e => e.recipe_id === recipeId && !e.batch_id);
  const dayList = [...new Set(fresh.map(e => e.day))].sort().map(weekdayShort);
  const names = [...new Set(fresh.map(e => members.value.find(m => m.id === e.user_id)?.name).filter(Boolean))];
  return [dayList.join(", "), names.join(", ")].filter(Boolean).join(" · ");
}
function openFreeze(recipeId: string, servings: number) {
  freezeRecipe.value = recipeId;
  freezeServings.value = servings;
  freezeDialog.value = true;
}
async function refreshAll() { await refresh(); await loadSummary(); }
function askWithdraw(id: string) { withdrawQuantity.value = Math.min(1, available(id)); withdrawBatch.value = id; }
function withdraw() {
  if (!withdrawBatch.value || !withdrawQuantity.value) return;
  run(async () => { await mutate("/movements", { id: crypto.randomUUID(), batch_id: withdrawBatch.value, kind: "withdraw", servings: withdrawQuantity.value }); withdrawBatch.value = null; });
}
function freeze() { const payload: BatchIn = { id: crypto.randomUUID(), recipe_id: freezeRecipe.value, servings: freezeServings.value, frozen_on: freezeDate.value, location: freezeLocation.value }; run(async () => { await mutate("/batches", payload); freezeDialog.value = false; }); }
// Average planned intake of the signed-in person over days that have meals this
// week. `incomplete` flags dishes without nutrition so the UI never shows a
// made-up zero as if it were a real value.
const weekAverage = computed(() => {
  const self = auth.user.value?.id;
  const perDay = new Map<string, { calories: number; protein: number }>();
  let incomplete = false;
  for (const e of currentPlan.value?.entries || []) {
    if (e.user_id !== self) continue;
    const facts = e.batch_id ? data.value?.state.batches?.[e.batch_id]?.facts : currentPlan.value?.recipe_snapshots?.[e.recipe_id] || data.value?.state.facts?.[e.recipe_id];
    if (facts?.per_serving.calories == null || facts?.per_serving.protein == null) incomplete = true;
    const day = perDay.get(e.day) || { calories: 0, protein: 0 };
    day.calories += (facts?.per_serving.calories || 0) * e.servings;
    day.protein += (facts?.per_serving.protein || 0) * e.servings;
    perDay.set(e.day, day);
  }
  if (!perDay.size) return null;
  const all = [...perDay.values()];
  return {
    calories: all.reduce((s, d) => s + d.calories, 0) / all.length,
    protein: all.reduce((s, d) => s + d.protein, 0) / all.length,
    days: all.length,
    incomplete,
  };
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
usePlannerPageRefresh(() => run(refreshAll), busy);
onMounted(() => run(refreshAll));
</script>

<style scoped>
.pp-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 16px;
  margin-bottom: var(--fork-stack);
}

.pp-toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pp-hint {
  margin-top: 12px;
  max-width: 70ch;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--fork-ink-soft);
}

/* One list surface with hairline rows instead of a card per item. */
.pp-list {
  margin: 0;
  padding: 0;
  list-style: none;
  background: rgb(var(--v-theme-surface));
  border: 1px solid var(--fork-hairline);
  border-radius: var(--fork-radius-card);
  overflow: hidden;
}

.pp-cook {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 10px 8px 10px 12px;
}

.pp-cook + .pp-cook {
  border-top: 1px solid var(--fork-hairline);
}

.pp-cook__qty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 52px;
  border-radius: var(--fork-radius-control);
  background: var(--fork-tint);
  color: rgb(var(--v-theme-primary));
  line-height: 1.1;
}

.pp-cook__qty strong {
  font-size: 1.25rem;
  font-variant-numeric: tabular-nums;
}

.pp-cook__qty span {
  font-size: 0.68rem;
  font-weight: 600;
}

.pp-cook__body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.pp-cook__name {
  color: inherit;
  font-weight: 650;
  line-height: 1.3;
  text-decoration: none;
  overflow-wrap: anywhere;
}

a.pp-cook__name:hover {
  text-decoration: underline;
}

.pp-cook__meta {
  margin-top: 2px;
  font-size: 0.8rem;
  color: var(--fork-ink-soft);
  text-transform: capitalize;
}

/* Freezer */
.pp-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 24px;
  margin-bottom: var(--fork-stack);
  padding: 14px 16px;
  border: 1px solid var(--fork-hairline);
  border-radius: var(--fork-radius-card);
  background: rgb(var(--v-theme-surface));
}

.pp-stat {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.pp-stat strong {
  font-size: 1.6rem;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.pp-stat span {
  font-size: 0.78rem;
  color: var(--fork-ink-soft);
}

.pp-stats__add {
  margin-left: auto;
}

.pp-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  margin-bottom: 12px;
}

.pp-filter > .v-text-field {
  flex: 1 1 240px;
}

.pp-filter > .v-switch {
  flex: none;
}

.pp-list--grid {
  display: grid;
  gap: 0;
}

.pp-batch {
  padding: 12px 12px 12px 14px;
}

.pp-batch + .pp-batch {
  border-top: 1px solid var(--fork-hairline);
}

.pp-batch.is-empty {
  opacity: 0.6;
}

.pp-batch__head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px;
}

.pp-batch__icon {
  margin-top: 0;
  color: var(--fork-frozen);
}

.pp-batch__title h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 650;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.pp-batch__title p {
  margin-top: 2px;
  font-size: 0.8rem;
  color: var(--fork-ink-soft);
}

.pp-batch__qty {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.1;
}

.pp-batch__qty strong {
  font-size: 1.35rem;
  font-variant-numeric: tabular-nums;
}

.pp-batch__qty span {
  font-size: 0.7rem;
  color: var(--fork-ink-soft);
}

.pp-batch__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
  padding-left: 34px;
}

.pp-batch__avail {
  font-size: 0.8rem;
  color: var(--fork-ink-soft);
}

.pp-batch__details {
  margin-top: 4px;
  padding-left: 34px;
  font-size: 0.82rem;
}

.pp-batch__details summary {
  min-height: 36px;
  padding: 8px 0;
  cursor: pointer;
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

@media (max-width: 599.98px) {
  .pp-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .pp-toolbar__actions > * {
    flex: 1 1 auto;
  }

  .pp-hide-xs {
    display: none;
  }

  .pp-stats__add {
    flex: 1 0 100%;
    margin-left: 0;
  }
}

@media (min-width: 960px) {
  .pp-list--grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .pp-list--grid .pp-batch + .pp-batch {
    border-top: 0;
  }

  .pp-list--grid .pp-batch:nth-child(n + 3) {
    border-top: 1px solid var(--fork-hairline);
  }

  .pp-list--grid .pp-batch:nth-child(even) {
    border-left: 1px solid var(--fork-hairline);
  }
}
</style>
