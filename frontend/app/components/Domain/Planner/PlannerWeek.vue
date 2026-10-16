<template>
  <div class="pw">
    <RecipeDialogAddToShoppingList v-model="shoppingDialog" :recipes="shoppingRecipes" :shopping-lists="shoppingLists" />

    <div class="pw-toolbar">
      <div class="pw-weeknav">
        <v-btn :icon="mdiChevronLeft" variant="text" :aria-label="t('previous')" :disabled="busy" @click="shiftWeek(-7)" />
        <div class="pw-weeklabel">
          <strong>{{ t('weekShort') }} {{ weekNumber }}</strong>
          <span>{{ shortDate(days[0]!) }} – {{ shortDate(days[6]!) }}</span>
        </div>
        <v-btn :icon="mdiChevronRight" variant="text" :aria-label="t('next')" :disabled="busy" @click="shiftWeek(7)" />
      </div>
      <div class="pw-actions">
        <v-btn
          variant="tonal"
          :prepend-icon="mdiCartOutline"
          :disabled="busy || !freshDishes.length"
          @click="prepareShopping"
        >
          {{ t('createShopping') }}
        </v-btn>
        <v-btn color="primary" :prepend-icon="mdiPlus" :disabled="busy || !data" @click="openPicker()">
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
    <div v-if="shoppingDone" class="pw-hint">
      <v-icon :icon="mdiCheck" size="18" />
      {{ t('shoppingAdded') }}
      <NuxtLink to="/shopping-lists">
        {{ t('toShopping') }}
      </NuxtLink>
    </div>
    <v-progress-linear v-if="busy && !data" indeterminate />

    <div v-if="data" class="pw-grid">
      <section v-for="day in days" :key="day" class="pw-day" :class="{ 'is-today': day === today }">
        <header class="pw-day__head">
          <span>{{ weekday(day) }}</span>
          <strong>{{ Number(day.slice(8)) }}.</strong>
        </header>
        <div v-for="meal in meals" :key="meal" class="pw-slot">
          <span class="pw-slot__label">{{ t(meal) }}</span>
          <button
            v-for="dish in dishesIn(day, meal)"
            :key="dish.recipeId"
            type="button"
            class="pw-dish"
            :class="{ 'is-eaten': dish.eaten }"
            @click="openEditor(dish.recipeId)"
          >
            <img v-if="dish.image" :src="dish.image" alt="" loading="lazy">
            <span v-else class="pw-dish__ph" aria-hidden="true"><v-icon :icon="mdiPotSteamOutline" size="16" /></span>
            <span class="pw-dish__name">{{ dish.name }}</span>
            <span class="pw-dish__people">
              <span v-for="m in dish.people" :key="m.id" class="pw-avatar" :style="{ background: m.color }" :title="m.name">{{ m.initial }}</span>
              <v-icon v-if="dish.frozen" :icon="mdiSnowflake" size="14" class="ml-1" />
            </span>
          </button>
          <button
            v-if="!dishesIn(day, meal).length"
            type="button"
            class="pw-empty"
            :aria-label="`${t('planDish')}: ${weekday(day)} ${t(meal)}`"
            @click="openPicker({ day, meal })"
          >
            <v-icon :icon="mdiPlus" size="16" />
          </button>
        </div>
        <footer class="pw-day__totals">
          <div v-for="m in memberList" :key="m.id" class="pw-total">
            <span class="pw-avatar" :style="{ background: m.color }">{{ m.initial }}</span>
            <span>{{ number(dayTotal(day, m.id).calories) }} kcal · {{ number(dayTotal(day, m.id).protein) }} g</span>
            <div v-if="m.id === selfId && goal" class="pw-bar" :title="`${t('dailyGoal')}: ${goal.calories} kcal`">
              <i :style="{ width: `${Math.min(100, (dayTotal(day, m.id).calories || 0) / goal.calories * 100)}%` }" />
            </div>
          </div>
        </footer>
      </section>
    </div>
    <p v-if="data && !recipes.length" class="pw-hint">
      {{ t('needFacts') }}
    </p>

    <v-dialog v-model="dialog" scrollable max-width="760" :fullscreen="$vuetify.display.xs">
      <v-card rounded="xl">
        <template v-if="step === 'pick'">
          <v-card-title class="pw-dialog__title">
            {{ t('chooseDish') }}
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model="search"
              :prepend-inner-icon="mdiMagnify"
              :label="t('searchDish')"
              variant="outlined"
              density="comfortable"
              hide-details
              clearable
              autofocus
              class="mb-4"
            />
            <div class="pw-picklist">
              <button v-for="r in filteredRecipes" :key="r.recipe_id" type="button" class="pw-pick" @click="choose(r.recipe_id)">
                <img v-if="r.image" :src="imageFor(r.recipe_id)" alt="" loading="lazy">
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
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="dialog = false">
              {{ t('close') }}
            </v-btn>
          </v-card-actions>
        </template>

        <template v-else-if="chosen">
          <v-card-title class="pw-dialog__title">
            <v-btn
              v-if="!editing"
              :icon="mdiArrowLeft"
              variant="text"
              size="small"
              :aria-label="t('back')"
              @click="step = 'pick'"
            />
            {{ chosen.name }}
          </v-card-title>
          <v-card-subtitle>{{ t('whenWho') }}</v-card-subtitle>
          <v-card-text>
            <div class="pw-matrix" role="grid">
              <div class="pw-matrix__row pw-matrix__head" role="row">
                <span />
                <span v-for="meal in meals" :key="meal" role="columnheader">{{ t(meal) }}</span>
              </div>
              <div v-for="day in days" :key="day" class="pw-matrix__row" role="row">
                <span class="pw-matrix__day" role="rowheader">{{ weekday(day) }} {{ Number(day.slice(8)) }}.</span>
                <div v-for="meal in meals" :key="meal" class="pw-matrix__cell" role="gridcell">
                  <div class="pw-toggles">
                    <button
                      v-for="m in memberList"
                      :key="m.id"
                      type="button"
                      class="pw-toggle"
                      :style="{ '--c': m.color }"
                      :aria-pressed="isSelected(m.id, day, meal)"
                      :disabled="!!blockedReason(m.id, day, meal)"
                      :title="blockedReason(m.id, day, meal) || m.name"
                      @click="toggle(m.id, day, meal)"
                    >
                      {{ m.initial }}
                    </button>
                  </div>
                  <small v-for="note in replaceNotes(day, meal)" :key="note" class="pw-replace">{{ note }}</small>
                </div>
              </div>
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
              <h4>{{ t('markEaten') }}</h4>
              <div v-for="e in eatable" :key="e.id" class="pw-eat__row">
                <span>{{ weekday(e.day) }} · {{ t(e.meal) }} · {{ memberName(e.user_id) }}</span>
                <v-btn size="small" variant="tonal" :prepend-icon="mdiCheck" :disabled="busy" @click="consume(e.id!)">
                  {{ t(e.batch_id ? 'withdraw' : 'eaten') }}
                </v-btn>
              </div>
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn v-if="editing" color="error" variant="text" :disabled="busy" @click="removeDish">
              {{ t('removeFromWeek') }}
            </v-btn>
            <v-spacer />
            <v-btn @click="dialog = false">
              {{ t('close') }}
            </v-btn>
            <v-btn color="primary" variant="flat" :loading="busy" @click="saveDish">
              {{ t('save') }}
            </v-btn>
          </v-card-actions>
        </template>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import {
  mdiArrowLeft,
  mdiCartOutline,
  mdiCheck,
  mdiChevronLeft,
  mdiChevronRight,
  mdiMagnify,
  mdiPlus,
  mdiPotSteamOutline,
  mdiSnowflake,
} from "@mdi/js";
import { addDays, format, getISOWeek, parseISO, startOfWeek } from "date-fns";
import RecipeDialogAddToShoppingList, { type RecipeWithScale } from "~/components/Domain/Recipe/RecipeDialogAddToShoppingList.vue";
import { useUserApi } from "~/composables/api";
import { useHouseholdPlanner } from "~/composables/use-household-planner";
import { useAddToShoppingListDialog } from "~/composables/shopping-list-page/use-add-to-shopping-list-dialog";
import type { AllocationIn, RecipeFactsOut } from "~/lib/api/types/household-planner";

type Meal = "breakfast" | "lunch" | "dinner";
type MemberInfo = {
  id: string;
  name: string;
  meal_preferences?: { gluten_free?: boolean; lactose_free?: boolean; avoid_traces?: boolean };
};

const i18n = useI18n();
const auth = useMealieAuth();
const t = (key: string) => i18n.t(`household-planner.${key}`);
const { api, data, personal, members, busy, error, run, refresh } = useHouseholdPlanner();
const nativeApi = useUserApi();
const { shoppingLists, open: shoppingDialog, getShoppingLists } = useAddToShoppingListDialog();

const meals: Meal[] = ["breakfast", "lunch", "dinner"];
const palette = ["rgb(var(--v-theme-primary))", "rgb(var(--v-theme-secondary))", "rgb(var(--v-theme-accent))"];
const today = format(new Date(), "yyyy-MM-dd");
const route = useRoute();
const week = ref(typeof route.query.week === "string" ? route.query.week : format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd"));
const days = computed(() => Array.from({ length: 7 }, (_, i) => format(addDays(parseISO(week.value), i), "yyyy-MM-dd")));
const weekNumber = computed(() => getISOWeek(parseISO(week.value)));
const selfId = computed(() => auth.user.value?.id || "");
const goal = computed(() => personal.value?.state.active?.goals);

const memberList = computed(() => (members.value as MemberInfo[]).map((m, i) => ({
  ...m,
  initial: (m.name || "?").trim().charAt(0).toUpperCase(),
  color: palette[i % palette.length]!,
})));
const memberName = (id: string) => memberList.value.find(m => m.id === id)?.name || "";

const plan = computed(() => Object.values(data.value?.state.plans || {}).find(p => p.start === week.value));
const entries = computed<AllocationIn[]>(() => plan.value?.entries || []);
const consumed = computed(() => new Set(plan.value?.consumed || []));
const recipes = computed(() => Object.values(data.value?.state.facts || {}).sort((a, b) => a.name.localeCompare(b.name)));

const number = (v: number | null | undefined) => v == null ? "—" : new Intl.NumberFormat(i18n.locale.value, { maximumFractionDigits: 0 }).format(v);
const shortDate = (d: string) => new Intl.DateTimeFormat(i18n.locale.value, { day: "numeric", month: "short" }).format(parseISO(d));
const weekday = (d: string) => new Intl.DateTimeFormat(i18n.locale.value, { weekday: "short" }).format(parseISO(d));
const imageFor = (recipeId: string) => `/api/media/recipes/${recipeId}/images/min-original.webp`;

function factsFor(e: AllocationIn): RecipeFactsOut | undefined {
  if (e.batch_id) return data.value?.state.batches?.[e.batch_id]?.facts;
  return plan.value?.recipe_snapshots?.[e.recipe_id] || data.value?.state.facts?.[e.recipe_id];
}

function dishesIn(day: string, meal: Meal) {
  const groups = new Map<string, { recipeId: string; name: string; image: string | null; people: typeof memberList.value; eaten: boolean; frozen: boolean }>();
  for (const e of entries.value.filter(x => x.day === day && x.meal === meal)) {
    const facts = factsFor(e);
    const group = groups.get(e.recipe_id) || {
      recipeId: e.recipe_id,
      name: facts?.name || "?",
      image: facts?.image ? imageFor(e.recipe_id) : null,
      people: [],
      eaten: true,
      frozen: false,
    };
    const member = memberList.value.find(m => m.id === e.user_id);
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
    for (const m of memberList.value) {
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
  const prefs = (members.value as MemberInfo[]).find(m => m.id === userId)?.meal_preferences;
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

const restrictionNote = computed(() => memberList.value
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

function shiftWeek(n: number) {
  week.value = format(addDays(parseISO(week.value), n), "yyyy-MM-dd");
  shoppingDone.value = false;
}

// ---- Shopping -----------------------------------------------------------
const shoppingRecipes = ref<RecipeWithScale[]>([]);
const shoppingDone = ref(false);
const freshDishes = computed(() => {
  const counts = new Map<string, number>();
  for (const e of entries.value) {
    if (e.batch_id) continue;
    counts.set(e.recipe_id, (counts.get(e.recipe_id) || 0) + e.servings);
  }
  return [...counts.entries()];
});

function prepareShopping() {
  run(async () => {
    const result: RecipeWithScale[] = [];
    for (const [recipeId, servings] of freshDishes.value) {
      const slug = data.value?.state.facts?.[recipeId]?.slug;
      if (!slug) throw new Error(t("shoppingRecipeMissing"));
      const response = await nativeApi.recipes.getOne(slug);
      if (response.error || !response.data) throw new Error(t("shoppingRecipeMissing"));
      const recipe = response.data;
      if (!recipe.recipeServings || recipe.recipeServings <= 0) throw new Error(`${recipe.name}: ${t("shoppingYieldMissing")}`);
      result.push({ ...recipe, scale: servings / recipe.recipeServings });
    }
    shoppingRecipes.value = result;
    await getShoppingLists();
    shoppingDialog.value = true;
  });
}
watch(shoppingDialog, (open, wasOpen) => {
  if (wasOpen && !open) shoppingDone.value = true;
});

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
  --pw-line: rgba(var(--v-theme-on-surface), 0.09);
  --pw-soft: rgba(var(--v-theme-on-surface), 0.62);
  padding: 8px 16px 32px;
}

.pw-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.pw-weeknav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pw-weeklabel {
  display: flex;
  flex-direction: column;
  min-width: 132px;
  text-align: center;
  line-height: 1.2;
}

.pw-weeklabel span {
  font-size: 0.82rem;
  color: var(--pw-soft);
}

.pw-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pw-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0 14px;
  color: var(--pw-soft);
}

.pw-hint a {
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

.pw-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
}

.pw-day {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: rgb(var(--v-theme-surface));
  border: 1px solid var(--pw-line);
  border-radius: 14px;
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

.pw-day__head span {
  font-size: 0.8rem;
  color: var(--pw-soft);
  text-transform: capitalize;
}

.pw-day__head strong {
  font-size: 1.15rem;
  letter-spacing: -0.02em;
}

.pw-slot {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 92px;
  padding: 8px 10px;
  border-top: 1px solid var(--pw-line);
}

.pw-slot__label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--pw-soft);
}

.pw-dish {
  display: grid;
  grid-template-columns: 34px 1fr;
  grid-template-rows: auto auto;
  column-gap: 8px;
  align-items: center;
  width: 100%;
  padding: 6px;
  border: 1px solid var(--pw-line);
  border-radius: 10px;
  background: rgb(var(--v-theme-background));
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.pw-dish:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
}

.pw-dish.is-eaten {
  opacity: 0.55;
}

.pw-dish img,
.pw-dish__ph {
  grid-row: span 2;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  object-fit: cover;
}

.pw-dish__ph {
  display: grid;
  place-items: center;
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}

.pw-dish__name {
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.25;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
}

.pw-dish__people {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-top: 3px;
}

.pw-avatar {
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  color: #fff;
  font-size: 0.66rem;
  font-weight: 700;
  flex: none;
}

.pw-empty {
  display: grid;
  place-items: center;
  flex: 1;
  min-height: 44px;
  border: 1px dashed var(--pw-line);
  border-radius: 10px;
  background: transparent;
  color: var(--pw-soft);
  cursor: pointer;
}

.pw-empty:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
  color: rgb(var(--v-theme-primary));
}

.pw-day__totals {
  margin-top: auto;
  padding: 8px 10px 10px;
  border-top: 1px solid var(--pw-line);
  font-size: 0.74rem;
  font-variant-numeric: tabular-nums;
}

.pw-total {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.pw-total + .pw-total {
  margin-top: 4px;
}

.pw-bar {
  flex-basis: 100%;
  height: 4px;
  border-radius: 4px;
  background: var(--pw-line);
  overflow: hidden;
}

.pw-bar i {
  display: block;
  height: 100%;
  background: rgb(var(--v-theme-primary));
}

/* Dialog */
.pw-dialog__title {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-top: 18px;
  font-weight: 700;
}

.pw-picklist {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.pw-pick {
  display: flex;
  gap: 10px;
  padding: 8px;
  border: 1px solid var(--pw-line);
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.pw-pick:hover {
  border-color: rgba(var(--v-theme-primary), 0.55);
}

.pw-pick img,
.pw-pick .pw-dish__ph {
  width: 64px;
  height: 64px;
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
  color: var(--pw-soft);
}

.pw-pick__body strong {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.92rem;
  line-height: 1.25;
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
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}

.pw-badges em.is-stock {
  background: rgba(var(--v-theme-accent), 0.12);
  color: rgb(var(--v-theme-accent));
}

.pw-matrix {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pw-matrix__row {
  display: grid;
  grid-template-columns: 64px repeat(3, minmax(0, 1fr));
  gap: 6px;
  align-items: start;
}

.pw-matrix__head span {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--pw-soft);
  text-align: center;
}

.pw-matrix__day {
  padding-top: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: capitalize;
}

.pw-matrix__cell {
  padding: 6px;
  border: 1px solid var(--pw-line);
  border-radius: 10px;
  min-height: 48px;
}

.pw-toggles {
  display: flex;
  justify-content: center;
  gap: 6px;
}

.pw-toggle {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1.5px solid var(--c);
  background: transparent;
  color: var(--c);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.pw-toggle[aria-pressed="true"] {
  background: var(--c);
  color: #fff;
}

.pw-toggle:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.pw-toggle:focus-visible,
.pw-dish:focus-visible,
.pw-pick:focus-visible,
.pw-empty:focus-visible {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.pw-replace {
  display: block;
  margin-top: 4px;
  font-size: 0.68rem;
  line-height: 1.2;
  color: rgb(var(--v-theme-warning));
  text-align: center;
}

.pw-note {
  margin-top: 12px;
  font-size: 0.82rem;
  color: var(--pw-soft);
}

.pw-eat {
  margin-top: 18px;
}

.pw-eat h4 {
  font-size: 0.9rem;
  margin-bottom: 6px;
}

.pw-eat__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid var(--pw-line);
  font-size: 0.85rem;
}

@media (max-width: 1100px) {
  .pw-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }
}

@media (max-width: 600px) {
  .pw {
    padding-inline: 12px;
  }

  .pw-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .pw-weeknav {
    justify-content: space-between;
  }

  .pw-actions > * {
    flex: 1;
  }

  .pw-grid {
    grid-template-columns: 1fr;
  }

  .pw-slot {
    min-height: 0;
  }

  .pw-matrix__row {
    grid-template-columns: 48px repeat(3, minmax(0, 1fr));
  }

  .pw-toggle {
    width: 30px;
    height: 30px;
  }
}
</style>
