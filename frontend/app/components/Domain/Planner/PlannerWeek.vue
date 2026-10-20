<template>
  <div class="pw">
    <PlannerShoppingDialog v-if="plan && data" v-model="shoppingDialog" :plan-id="plan.id!" :revision="data.revision" @added="linked" />

    <div class="pw-toolbar">
      <PlannerWeekNav v-model="week" :disabled="busy" />
      <div class="pw-actions">
        <v-btn
          v-if="plan?.shopping_list_id"
          variant="tonal"
          color="primary"
          :prepend-icon="mdiCartOutline"
          :to="`/shopping-lists/${plan.shopping_list_id}`"
        >
          {{ t('openShopping') }}
        </v-btn>
        <v-btn
          v-else
          variant="tonal"
          color="primary"
          :prepend-icon="mdiCartOutline"
          :disabled="busy || !freshDishes.length"
          @click="shoppingDialog = true"
        >
          {{ t('createShopping') }}
        </v-btn>
        <v-btn color="primary" variant="flat" :prepend-icon="mdiPlus" :disabled="busy || !data" @click="openPicker()">
          {{ t('planDish') }}
        </v-btn>
      </div>
    </div>

    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
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
      <NuxtLink :to="plan?.shopping_list_id ? `/shopping-lists/${plan.shopping_list_id}` : '/shopping-lists'" class="pw-link">
        {{ t('toShopping') }}
      </NuxtLink>
    </v-alert>
    <v-progress-linear v-if="busy && !data" indeterminate />

    <div v-if="data && !recipes.length" class="fork-empty mb-4">
      <v-icon :icon="mdiPotSteamOutline" size="32" />
      <strong>{{ t('noFactsTitle') }}</strong>
      <p>{{ t('needFacts') }}</p>
    </div>

    <div v-if="data" class="pw-grid">
      <section v-for="day in days" :key="day" class="pw-day" :class="{ 'is-today': day === today }" :aria-label="longDay(day)">
        <header class="pw-day__head">
          <span class="pw-day__name">{{ weekday(day) }}</span>
          <strong>{{ Number(day.slice(8)) }}.</strong>
          <span v-if="day === today" class="pw-day__today">{{ t('today') }}</span>
        </header>
        <div v-for="meal in meals" :key="meal" class="pw-slot">
          <span class="pw-slot__label">{{ t(meal) }}</span>
          <div class="pw-slot__dishes">
            <button
              v-for="dish in dishesIn(day, meal)"
              :key="dish.recipeId"
              type="button"
              class="pw-dish"
              :class="{ 'is-eaten': dish.eaten }"
              :aria-label="`${dish.name}, ${dish.people.map(p => p.name).join(', ')}`"
              @click="openEditor(dish.recipeId)"
            >
              <img v-if="dish.image" :src="recipeSmallImage(dish.recipeId, dish.image)" alt="" loading="lazy">
              <span v-else class="pw-dish__ph" aria-hidden="true"><v-icon :icon="mdiPotSteamOutline" size="16" /></span>
              <span class="pw-dish__name">{{ dish.name }}</span>
              <span class="pw-dish__people" aria-hidden="true">
                <span v-for="m in dish.people" :key="m.id" class="fork-person" :style="{ '--c': m.color }" :title="m.name">{{ m.label }}</span>
                <v-icon v-if="dish.frozen" :icon="mdiSnowflake" size="14" class="pw-frozen" :title="t('fromFreezer')" />
                <v-icon v-if="dish.eaten" :icon="mdiCheck" size="14" :title="t('eaten')" />
              </span>
            </button>
            <button
              v-if="!dishesIn(day, meal).length"
              type="button"
              class="pw-empty"
              :aria-label="`${t('planDish')}: ${longDay(day)}, ${t(meal)}`"
              @click="openPicker({ day, meal })"
            >
              <v-icon :icon="mdiPlus" size="18" />
            </button>
          </div>
        </div>
        <footer v-if="totalsFor(day).length" class="pw-day__totals">
          <div v-for="row in totalsFor(day)" :key="row.person.id" class="pw-total">
            <span class="fork-person" :style="{ '--c': row.person.color }" :title="row.person.name">{{ row.person.label }}</span>
            <span v-if="row.calories == null" class="pw-total__value is-unknown">{{ t('nutritionUnknown') }}</span>
            <span v-else class="pw-total__value">{{ number(row.calories) }} kcal · {{ number(row.protein) }} g {{ t('proteinShort') }}</span>
            <template v-if="row.goal && row.calories != null">
              <span class="pw-total__pct">{{ Math.round(row.calories / row.goal * 100) }} %</span>
              <div
                class="pw-bar"
                role="progressbar"
                :aria-valuenow="Math.round(row.calories)"
                aria-valuemin="0"
                :aria-valuemax="row.goal"
                :aria-label="`${t('ofDailyGoal')} ${number(row.goal)} kcal`"
              >
                <i :class="{ 'is-over': row.calories > row.goal * 1.05 }" :style="{ width: `${Math.min(100, row.calories / row.goal * 100)}%` }" />
              </div>
            </template>
          </div>
        </footer>
      </section>
    </div>
    <p v-if="data && goal" class="pw-legend">
      {{ t('goalLegend') }} {{ number(goal.calories) }} kcal
    </p>

    <PlannerSheet
      v-model="dialog"
      fullscreen
      max-width="760"
      :title="step === 'pick' || !chosen ? t('chooseDish') : chosen.name"
      :subtitle="step === 'pick' || !chosen ? '' : t('whenWho')"
    >
      <template v-if="step === 'when' && !editing" #prepend>
        <v-btn :icon="mdiArrowLeft" variant="text" :aria-label="t('back')" @click="step = 'pick'" />
      </template>

      <template v-if="step === 'pick'">
        <v-text-field
          v-model="search"
          :prepend-inner-icon="mdiMagnify"
          :label="t('searchDish')"
          variant="outlined"
          density="comfortable"
          hide-details
          clearable
          class="mb-4"
        />
        <div class="pw-picklist">
          <button v-for="r in filteredRecipes" :key="r.recipe_id" type="button" class="pw-pick" @click="choose(r.recipe_id)">
            <img v-if="r.image" :src="recipeSmallImage(r.recipe_id, r.image)" alt="" loading="lazy">
            <span v-else class="pw-dish__ph" aria-hidden="true"><v-icon :icon="mdiPotSteamOutline" /></span>
            <span class="pw-pick__body">
              <strong>{{ r.name }}</strong>
              <span>{{ number(r.per_serving.calories) }} kcal · {{ number(r.per_serving.protein) }} g {{ t('protein') }}</span>
              <span class="pw-badges">
                <em v-if="r.gluten_free === 'yes'">{{ t('gfShort') }}</em>
                <em v-if="r.lactose_free === 'yes'">{{ t('lfShort') }}</em>
                <em v-if="stockFor(r.recipe_id) > 0" class="is-stock"><v-icon :icon="mdiSnowflake" size="12" /> {{ number(stockFor(r.recipe_id)) }} {{ t('inStock') }}</em>
              </span>
            </span>
          </button>
        </div>
        <p v-if="!filteredRecipes.length" class="pw-note">
          {{ t('noDishMatches') }}
        </p>
      </template>

      <template v-else-if="chosen">
        <div class="pw-plan">
          <section v-for="day in days" :key="day" class="pw-plan__day" :class="{ 'is-today': day === today }">
            <h3 class="pw-plan__dayname">
              {{ weekday(day) }} {{ Number(day.slice(8)) }}.
            </h3>
            <div v-for="meal in meals" :key="meal" class="pw-plan__meal">
              <span class="pw-plan__meallabel">{{ t(meal) }}</span>
              <div class="pw-chips">
                <button
                  v-for="m in people"
                  :key="m.id"
                  type="button"
                  class="pw-chip"
                  :style="{ '--c': m.color }"
                  :aria-pressed="isSelected(m.id, day, meal)"
                  :aria-label="`${m.name}, ${longDay(day)}, ${t(meal)}`"
                  :disabled="!!blockedReason(m.id, day, meal)"
                  :title="blockedReason(m.id, day, meal) || m.name"
                  @click="toggle(m.id, day, meal)"
                >
                  <v-icon v-if="isSelected(m.id, day, meal)" :icon="mdiCheck" size="16" />
                  <v-icon v-else-if="blockedReason(m.id, day, meal)" :icon="mdiLockOutline" size="14" />
                  {{ m.name }}
                </button>
              </div>
              <small v-for="note in replaceNotes(day, meal)" :key="note" class="pw-replace">{{ note }}</small>
            </div>
          </section>
        </div>
        <p v-if="restrictionNote" class="pw-note">
          {{ restrictionNote }}
        </p>
        <v-switch
          v-if="stockFor(chosen.recipe_id) > 0"
          v-model="useFreezer"
          color="primary"
          hide-details
          density="compact"
          class="mt-3"
          :label="`${t('useFreezer')} (${number(stockFor(chosen.recipe_id))} ${t('inStock')})`"
        />
        <div v-if="eatable.length" class="pw-eat">
          <h4 class="fork-section-title">
            {{ t('markEaten') }}
          </h4>
          <div v-for="e in eatable" :key="e.id" class="pw-eat__row">
            <span>{{ weekday(e.day) }} · {{ t(e.meal) }} · {{ memberName(e.user_id) }}</span>
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              :prepend-icon="mdiCheck"
              :disabled="busy"
              @click="consume(e.id!)"
            >
              {{ t(e.batch_id ? 'withdraw' : 'eaten') }}
            </v-btn>
          </div>
        </div>
      </template>

      <template v-if="step === 'when' && chosen" #actions>
        <v-btn
          v-if="editing"
          color="error"
          variant="text"
          :prepend-icon="mdiDeleteOutline"
          :disabled="busy"
          @click="removeDish"
        >
          {{ t('removeFromWeek') }}
        </v-btn>
        <v-spacer />
        <v-btn color="primary" variant="flat" :loading="busy" @click="saveDish">
          {{ t('save') }}
        </v-btn>
      </template>
    </PlannerSheet>
  </div>
</template>

<script setup lang="ts">
import {
  mdiArrowLeft,
  mdiCartOutline,
  mdiCheck,
  mdiDeleteOutline,
  mdiLockOutline,
  mdiMagnify,
  mdiPlus,
  mdiPotSteamOutline,
  mdiSnowflake,
} from "@mdi/js";
import { addDays, format, parseISO, startOfWeek } from "date-fns";
import { useStaticRoutes } from "~/composables/api";
import { useHouseholdPlanner } from "~/composables/use-household-planner";
import type { AllocationIn, RecipeFactsOut, StateOut } from "~/lib/api/types/household-planner";
import { toPeople, type PlannerMember } from "~/lib/planner/people";
import { usePlannerPageRefresh } from "~/composables/use-planner-page";
import PlannerSheet from "~/components/Domain/Planner/PlannerSheet.vue";
import PlannerShoppingDialog from "~/components/Domain/Planner/PlannerShoppingDialog.vue";
import PlannerWeekNav from "~/components/Domain/Planner/PlannerWeekNav.vue";

type Meal = "breakfast" | "lunch" | "dinner";

const i18n = useI18n();
const auth = useMealieAuth();
const t = (key: string) => i18n.t(`household-planner.${key}`);
const { api, data, personal, members, busy, error, run, refresh } = useHouseholdPlanner();

const meals: Meal[] = ["breakfast", "lunch", "dinner"];
const today = format(new Date(), "yyyy-MM-dd");
const route = useRoute();
const week = ref(typeof route.query.week === "string" ? route.query.week : format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd"));
const days = computed(() => Array.from({ length: 7 }, (_, i) => format(addDays(parseISO(week.value), i), "yyyy-MM-dd")));
const selfId = computed(() => auth.user.value?.id || "");
const goal = computed(() => personal.value?.state.active?.goals);

const people = computed(() => toPeople(members.value as PlannerMember[]));
const memberName = (id: string) => people.value.find(m => m.id === id)?.name || "";

const plan = computed(() => Object.values(data.value?.state.plans || {}).find(p => p.start === week.value));
const entries = computed<AllocationIn[]>(() => plan.value?.entries || []);
const consumed = computed(() => new Set(plan.value?.consumed || []));
const recipes = computed(() => Object.values(data.value?.state.facts || {}).sort((a, b) => a.name.localeCompare(b.name)));

const number = (v: number | null | undefined) => v == null ? "—" : new Intl.NumberFormat(i18n.locale.value, { maximumFractionDigits: 0 }).format(v);
const weekday = (d: string) => new Intl.DateTimeFormat(i18n.locale.value, { weekday: "short" }).format(parseISO(d));
const longDay = (d: string) => new Intl.DateTimeFormat(i18n.locale.value, { weekday: "long", day: "numeric", month: "long" }).format(parseISO(d));
// The server fills `image` from the live recipe; the key versions the URL so a new photo shows at once.
const { recipeSmallImage } = useStaticRoutes();

function factsFor(e: AllocationIn): RecipeFactsOut | undefined {
  if (e.batch_id) return data.value?.state.batches?.[e.batch_id]?.facts;
  return plan.value?.recipe_snapshots?.[e.recipe_id] || data.value?.state.facts?.[e.recipe_id];
}

function dishesIn(day: string, meal: Meal) {
  const groups = new Map<string, { recipeId: string; name: string; image: string | null; people: typeof people.value; eaten: boolean; frozen: boolean }>();
  for (const e of entries.value.filter(x => x.day === day && x.meal === meal)) {
    const facts = factsFor(e);
    const group = groups.get(e.recipe_id) || {
      recipeId: e.recipe_id,
      name: facts?.name || "?",
      image: facts?.image || null,
      people: [],
      eaten: true,
      frozen: false,
    };
    const member = people.value.find(m => m.id === e.user_id);
    if (member) group.people.push(member);
    group.eaten &&= consumed.value.has(e.id!);
    group.frozen ||= !!e.batch_id;
    groups.set(e.recipe_id, group);
  }
  return [...groups.values()];
}

function dayTotal(day: string, userId: string) {
  let calories: number | null = 0;
  let protein: number | null = 0;
  for (const e of entries.value.filter(x => x.day === day && x.user_id === userId)) {
    const per = factsFor(e)?.per_serving;
    calories = calories == null || per?.calories == null ? null : calories + per.calories * e.servings;
    protein = protein == null || per?.protein == null ? null : protein + per.protein * e.servings;
  }
  return { calories, protein };
}

// Totals shown under a day: everyone who eats that day, plus yourself with
// your daily goal so the bar always has a reference.
function totalsFor(day: string) {
  const eating = new Set(entries.value.filter(e => e.day === day).map(e => e.user_id));
  return people.value
    .filter(p => eating.has(p.id))
    .map(person => ({ person, ...dayTotal(day, person.id), goal: person.id === selfId.value ? goal.value?.calories : undefined }));
}

// Frozen stock not reserved by other weeks' plans.
function capacity(batchId: string) {
  const batch = data.value?.state.batches?.[batchId];
  if (!batch) return 0;
  const reservedElsewhere = Object.values(data.value?.state.plans || {})
    .filter(p => p.start !== week.value)
    .flatMap(p => (p.entries || []).filter(e => e.batch_id === batchId && !p.consumed?.includes(e.id!)))
    .reduce((s, e) => s + e.servings, 0);
  return batch.remaining - reservedElsewhere;
}
const stockFor = (recipeId: string) => Object.values(data.value?.state.batches || {})
  .filter(b => b.recipe_id === recipeId)
  .reduce((s, b) => s + Math.max(0, capacity(b.id!)), 0);

// ---- Dish dialog --------------------------------------------------------
const dialog = ref(false);
const step = ref<"pick" | "when">("pick");
const editing = ref(false);
const search = ref("");
const chosenId = ref("");
const selected = ref(new Set<string>());
const useFreezer = ref(true);
const presetSlot = ref<{ day: string; meal: Meal } | null>(null);
const chosen = computed(() => data.value?.state.facts?.[chosenId.value]);
const filteredRecipes = computed(() => {
  const q = (search.value || "").toLocaleLowerCase();
  return recipes.value.filter(r => r.name.toLocaleLowerCase().includes(q));
});
const slotKey = (userId: string, day: string, meal: string) => `${userId}|${day}|${meal}`;
const isSelected = (userId: string, day: string, meal: Meal) => selected.value.has(slotKey(userId, day, meal));

function openPicker(slot: { day: string; meal: Meal } | null = null) {
  presetSlot.value = slot;
  editing.value = false;
  search.value = "";
  step.value = "pick";
  dialog.value = true;
}

function choose(recipeId: string) {
  chosenId.value = recipeId;
  const next = new Set(entries.value.filter(e => e.recipe_id === recipeId).map(e => slotKey(e.user_id, e.day, e.meal)));
  if (presetSlot.value) {
    for (const m of people.value) {
      if (!blockedReason(m.id, presetSlot.value.day, presetSlot.value.meal)) next.add(slotKey(m.id, presetSlot.value.day, presetSlot.value.meal));
    }
  }
  selected.value = next;
  useFreezer.value = stockFor(recipeId) > 0;
  step.value = "when";
}

function openEditor(recipeId: string) {
  presetSlot.value = null;
  editing.value = true;
  dialog.value = true;
  choose(recipeId);
}

function restricted(userId: string) {
  const prefs = (members.value as PlannerMember[]).find(m => m.id === userId)?.meal_preferences;
  const facts = chosen.value;
  if (!prefs || !facts) return "";
  if (prefs.gluten_free && facts.gluten_free !== "yes") return t("notVerifiedGf");
  if (prefs.lactose_free && facts.lactose_free !== "yes") return t("notVerifiedLf");
  return "";
}

function blockedReason(userId: string, day: string, meal: Meal) {
  const occupant = entries.value.find(e => e.user_id === userId && e.day === day && e.meal === meal);
  if (occupant && consumed.value.has(occupant.id!)) return t("eatenLocked");
  return restricted(userId);
}

const restrictionNote = computed(() => people.value
  .map(m => restricted(m.id) ? `${m.name}: ${restricted(m.id)}` : "")
  .filter(Boolean)
  .join(" · "));

function toggle(userId: string, day: string, meal: Meal) {
  const key = slotKey(userId, day, meal);
  const next = new Set(selected.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  selected.value = next;
}

function replaceNotes(day: string, meal: Meal) {
  const notes = new Set<string>();
  for (const e of entries.value) {
    if (e.day !== day || e.meal !== meal || e.recipe_id === chosenId.value) continue;
    if (!selected.value.has(slotKey(e.user_id, day, meal))) continue;
    notes.add(`${t("replaces")} ${factsFor(e)?.name || ""}`);
  }
  return [...notes];
}

const eatable = computed(() => entries.value
  .filter(e => e.recipe_id === chosenId.value && !consumed.value.has(e.id!) && e.day <= today)
  .sort((a, b) => `${a.day}${meals.indexOf(a.meal as Meal)}`.localeCompare(`${b.day}${meals.indexOf(b.meal as Meal)}`)));

async function writeWeek(next: AllocationIn[]) {
  if (!data.value) return;
  const payload = { id: plan.value?.id || crypto.randomUUID(), start: week.value, entries: next };
  data.value = await api.write(`/weeks/${week.value}`, payload, data.value.revision, "put");
}

function saveDish() {
  run(async () => {
    const recipeId = chosenId.value;
    // Keep other dishes except in slots this dish takes over; eaten entries always stay.
    const kept = entries.value.filter(e => consumed.value.has(e.id!)
      || (e.recipe_id !== recipeId && !selected.value.has(slotKey(e.user_id, e.day, e.meal))));
    const keptSlots = new Set(kept.map(e => slotKey(e.user_id, e.day, e.meal)));
    const previous = new Map(entries.value.filter(e => e.recipe_id === recipeId).map(e => [slotKey(e.user_id, e.day, e.meal), e]));
    const batches = Object.values(data.value?.state.batches || {})
      .filter(b => b.recipe_id === recipeId)
      .sort((a, b) => a.frozen_on.localeCompare(b.frozen_on))
      .map(b => ({ id: b.id!, left: capacity(b.id!) - kept.filter(e => e.batch_id === b.id).reduce((s, e) => s + e.servings, 0) }));
    const slots = [...selected.value]
      .filter(key => !keptSlots.has(key))
      .map(key => key.split("|") as [string, string, Meal])
      .sort((a, b) => `${a[1]}${meals.indexOf(a[2])}`.localeCompare(`${b[1]}${meals.indexOf(b[2])}`));
    const added: AllocationIn[] = slots.map(([userId, day, meal]) => {
      const old = previous.get(slotKey(userId, day, meal));
      const batch = useFreezer.value ? batches.find(b => b.left >= 1) : undefined;
      if (batch) batch.left -= 1;
      return { id: old?.id || crypto.randomUUID(), user_id: userId, recipe_id: recipeId, day, meal, servings: 1, batch_id: batch?.id || null, note: "" };
    });
    await writeWeek([...kept, ...added]);
    dialog.value = false;
  });
}

function removeDish() {
  run(async () => {
    await writeWeek(entries.value.filter(e => e.recipe_id !== chosenId.value || consumed.value.has(e.id!)));
    dialog.value = false;
  });
}

function consume(entryId: string) {
  run(async () => {
    if (!data.value || !plan.value) return;
    data.value = await api.write(`/plans/${plan.value.id}/consume/${entryId}`, {}, data.value.revision);
  });
}

watch(week, () => (shoppingDone.value = false));

// ---- Shopping -----------------------------------------------------------
const shoppingDialog = ref(false);
const shoppingDone = ref(false);
function linked(state: StateOut) {
  data.value = state;
  shoppingDone.value = true;
}
const freshDishes = computed(() => entries.value.filter(e => !e.batch_id));

usePlannerPageRefresh(() => run(refresh), busy);

onMounted(() => run(async () => {
  await refresh();
  // Coming from an idea: open the planning matrix for that dish right away.
  const recipeId = typeof route.query.plan === "string" ? route.query.plan : "";
  if (recipeId && data.value?.state.facts?.[recipeId]) {
    presetSlot.value = null;
    editing.value = false;
    dialog.value = true;
    choose(recipeId);
  }
}));
</script>

<style scoped>
.pw {
  container: planner-week / inline-size;
}

.pw-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--fork-stack);
}

.pw-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pw-link {
  margin-left: 4px;
  font-weight: 650;
  color: inherit;
}

.pw-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(272px, 1fr));
  gap: 12px;
}

.pw-day {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: rgb(var(--v-theme-surface));
  border: 1px solid var(--fork-hairline);
  border-radius: var(--fork-radius-card);
  overflow: hidden;
}

.pw-day.is-today {
  border-color: rgba(var(--v-theme-primary), 0.55);
  box-shadow: inset 0 3px 0 rgb(var(--v-theme-primary));
}

.pw-day__head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 10px 12px 6px;
}

.pw-day__name {
  font-size: 0.85rem;
  color: var(--fork-ink-soft);
  text-transform: capitalize;
}

.pw-day__head strong {
  font-size: 1.1rem;
  letter-spacing: -0.02em;
}

.pw-day__today {
  margin-left: auto;
  font-size: 0.72rem;
  font-weight: 700;
  color: rgb(var(--v-theme-primary));
}

/* Meal label beside the dishes: one line per meal instead of two. */
.pw-slot {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  padding: 6px 10px 6px 12px;
}

.pw-slot + .pw-slot {
  border-top: 1px solid var(--fork-hairline);
}

.pw-slot__label {
  padding-top: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--fork-ink-soft);
}

.pw-slot__dishes {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.pw-dish {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  column-gap: 8px;
  align-items: center;
  width: 100%;
  min-height: 44px;
  padding: 5px 6px;
  border: 1px solid var(--fork-hairline);
  border-radius: var(--fork-radius-control);
  background: rgb(var(--v-theme-background));
  color: inherit;
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.pw-dish:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
}

.pw-dish.is-eaten {
  opacity: 0.6;
}

.pw-dish img,
.pw-dish__ph {
  grid-row: span 2;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  object-fit: cover;
}

.pw-dish__ph {
  display: grid;
  place-items: center;
  background: var(--fork-tint);
  color: rgb(var(--v-theme-primary));
}

.pw-dish__name {
  font-size: 0.84rem;
  font-weight: 600;
  line-height: 1.25;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
}

.pw-dish__people {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 3px;
  margin-top: 3px;
}

.pw-dish__people .fork-person {
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  font-size: 0.64rem;
}

.pw-frozen {
  color: var(--fork-frozen);
}

.pw-empty {
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 44px;
  border: 1px dashed var(--fork-hairline-strong);
  border-radius: var(--fork-radius-control);
  background: transparent;
  color: var(--fork-ink-soft);
  cursor: pointer;
}

.pw-empty:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
  color: rgb(var(--v-theme-primary));
}

.pw-day__totals {
  display: grid;
  gap: 6px;
  margin-top: auto;
  padding: 8px 12px 10px;
  border-top: 1px solid var(--fork-hairline);
  background: rgba(var(--v-theme-on-surface), 0.02);
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
}

.pw-total {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 4px 8px;
}

.pw-total__value.is-unknown {
  color: var(--fork-ink-soft);
  font-style: italic;
}

.pw-total__pct {
  font-weight: 700;
}

.pw-bar {
  grid-column: 2 / -1;
  height: 5px;
  border-radius: 5px;
  background: var(--fork-hairline-strong);
  overflow: hidden;
}

.pw-bar i {
  display: block;
  height: 100%;
  background: rgb(var(--v-theme-primary));
}

.pw-bar i.is-over {
  background: rgb(var(--v-theme-warning));
}

.pw-legend {
  margin-top: 12px;
  font-size: 0.8rem;
  color: var(--fork-ink-soft);
}

/* Wide content area: seven columns, so the meal label goes above the dishes.
   A container query, because the sidebar decides how wide the content is. */
@container planner-week (min-width: 1120px) {
  .pw-grid {
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 8px;
  }

  .pw-slot {
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
    min-height: 96px;
  }

  .pw-slot__label {
    padding-top: 2px;
  }
}

@media (max-width: 599.98px) {
  .pw-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .pw-actions > * {
    flex: 1 1 auto;
  }

  .pw-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* Dialog ------------------------------------------------------------------ */
.pw-picklist {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
}

.pw-pick {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px;
  border: 1px solid var(--fork-hairline);
  border-radius: var(--fork-radius-control);
  background: rgb(var(--v-theme-surface));
  color: inherit;
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.pw-pick:hover {
  border-color: rgba(var(--v-theme-primary), 0.55);
}

.pw-pick img,
.pw-pick .pw-dish__ph {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  object-fit: cover;
  flex: none;
}

.pw-pick__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  font-size: 0.82rem;
  color: var(--fork-ink-soft);
}

.pw-pick__body strong {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.92rem;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.pw-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}

.pw-badges em {
  font-style: normal;
  font-size: 0.7rem;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--fork-tint);
  color: rgb(var(--v-theme-primary));
}

.pw-badges em.is-stock {
  background: color-mix(in srgb, var(--fork-frozen) 14%, transparent);
  color: var(--fork-frozen);
}

/* Planning list: one block per day, one row per meal, a chip per person.
   Works for two people and for six; chips wrap instead of overflowing. */
.pw-plan {
  display: flex;
  flex-direction: column;
}

.pw-plan__day {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 2px;
  padding: 10px 0;
}

.pw-plan__day + .pw-plan__day {
  border-top: 1px solid var(--fork-hairline);
}

.pw-plan__day.is-today .pw-plan__dayname {
  color: rgb(var(--v-theme-primary));
}

.pw-plan__dayname {
  font-size: 0.92rem;
  font-weight: 700;
  text-transform: capitalize;
}

.pw-plan__meal {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  align-items: center;
  gap: 4px 8px;
  padding: 3px 0;
}

.pw-plan__meallabel {
  font-size: 0.82rem;
  color: var(--fork-ink-soft);
}

.pw-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.pw-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 40px;
  max-width: 100%;
  padding: 0 12px;
  border: 1.5px solid color-mix(in srgb, var(--c) 45%, transparent);
  border-radius: 999px;
  background: transparent;
  color: var(--c);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.v-theme--dark .pw-chip {
  color: rgb(var(--v-theme-on-surface));
}

.pw-chip[aria-pressed="true"] {
  border-color: var(--c);
  background: var(--c);
  color: #fff;
}

.pw-chip:disabled {
  border-style: dashed;
  color: var(--fork-ink-soft);
  border-color: var(--fork-hairline-strong);
  cursor: not-allowed;
}

.pw-replace {
  grid-column: 2;
  font-size: 0.75rem;
  line-height: 1.3;
  color: rgb(var(--v-theme-warning));
}

.pw-note {
  margin-top: 12px;
  font-size: 0.85rem;
  color: var(--fork-ink-soft);
}

.pw-eat {
  margin-top: 16px;
}

.pw-eat h4 {
  margin-bottom: 6px;
}

.pw-eat__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid var(--fork-hairline);
  font-size: 0.88rem;
}

@media (min-width: 600px) {
  .pw-plan__day {
    grid-template-columns: 64px repeat(3, minmax(0, 1fr));
    gap: 10px;
    align-items: start;
  }

  .pw-plan__dayname {
    padding-top: 22px;
  }

  .pw-plan__meal {
    grid-template-columns: minmax(0, 1fr);
    align-content: start;
  }

  .pw-replace {
    grid-column: 1;
  }
}
</style>
