<template>
  <v-container class="planner-shell">
    <header class="planner-heading">
      <div><span class="eyebrow">{{ t('eyebrow') }}</span><h1>{{ t(navigation.find(n => n.value === tab)?.label || 'navWeek') }}</h1></div>
      <v-btn :icon="mdiRefresh" variant="text" :aria-label="t('refresh')" :loading="busy" @click="run(refreshAll)" />
    </header>
    <nav class="planner-navigation" :aria-label="t('navigation')">
      <button v-for="item in navigation" :key="item.value" type="button" :aria-current="tab === item.value ? 'page' : undefined" @click="changeTab(item.value)">
        <v-icon :icon="item.icon" size="23" /><span>{{ t(item.label) }}</span>
      </button>
    </nav>
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
      <div v-if="['week', 'cook', 'shopping'].includes(tab)" class="week-navigation">
        <v-btn :icon="mdiChevronLeft" variant="text" :aria-label="t('previous')" :disabled="busy" @click="requestWeekShift(-7)" />
        <strong>{{ weekLabel }}</strong>
        <v-btn :icon="mdiChevronRight" variant="text" :aria-label="t('next')" :disabled="busy" @click="requestWeekShift(7)" />
      </div>
      <section v-if="tab === 'week'" :aria-label="t('week')">
        <div class="person-switch" role="group" :aria-label="t('person')">
          <button v-for="member in members" :key="member.id" type="button" :aria-pressed="person === member.id" @click="person = member.id">
            {{ member.name }}
          </button>
        </div>
        <div class="day-strip" role="group" :aria-label="t('chooseDay')">
          <button
            v-for="day in days"
            :key="day"
            type="button"
            :aria-pressed="selectedDay === day"
            :aria-label="`${dayLabel(day)} ${shortDate(day)}`"
            :class="{ 'is-today': day === today }"
            @click="selectDay(day)"
          >
            <span>{{ dayLabel(day) }}</span><strong>{{ Number(day.slice(8)) }}</strong><i :class="{ filled: entriesFor(day).length }" />
          </button>
        </div>
        <div class="day-actions">
          <h2>{{ selectedDay === today ? t('today') : dayLabel(selectedDay) }} <span>{{ shortDate(selectedDay) }}</span></h2>
          <v-btn variant="text" size="small" :aria-expanded="showOverview" @click="showOverview = !showOverview">
            {{ t('overview') }}
          </v-btn>
          <v-menu v-if="currentPlan">
            <template #activator="{ props }">
              <v-btn v-bind="props" :icon="mdiDotsHorizontal" variant="text" :aria-label="t('planActions')" />
            </template><v-list><v-list-item :title="t('cancelPlan')" :disabled="busy" @click="cancelDialog = true" /></v-list>
          </v-menu>
        </div>
        <div v-if="showOverview" class="week-overview">
          <button v-for="day in days" :key="day" type="button" @click="selectDay(day)">
            <span>{{ dayLabel(day) }} · {{ shortDate(day) }}</span><strong>{{ number(dayTotal(day)?.nutrients.calories) }} kcal</strong><v-icon :icon="mdiChevronRight" size="20" />
          </button>
        </div>
        <div class="daily-summary">
          <div><span>{{ t('plannedEnergy') }}</span><strong>{{ number(dayTotal(selectedDay)?.nutrients.calories) }} <small>kcal</small></strong></div>
          <div><span>{{ t('protein') }}</span><strong>{{ number(dayTotal(selectedDay)?.nutrients.protein) }} <small>g</small></strong></div>
          <p v-if="dayTotal(selectedDay)">
            {{ dayTotal(selectedDay)?.known_entries }}/{{ dayTotal(selectedDay)?.entries }} {{ t('complete') }}
          </p>
          <p v-else>
            {{ t('previewForTotals') }}
          </p>
        </div>
        <div class="meal-list">
          <article v-for="entry in entriesFor(selectedDay)" :key="entry.id" class="meal-card" :class="{ recorded: currentPlan?.consumed?.includes(entry.id!) }">
            <NuxtLink :to="`/g/${auth.user.value?.groupSlug}/r/${factsFor(entry)?.slug}`" class="meal-main">
              <img v-if="factsFor(entry)?.image" :src="`/api/media/recipes/${entry.recipe_id}/images/min-original.webp`" alt="" loading="lazy">
              <div v-else class="meal-placeholder" aria-hidden="true"><v-icon :icon="mdiPotSteamOutline" size="30" /></div>
              <div class="meal-copy">
                <span class="meal-label">{{ t(entry.meal) }}<span v-if="entry.batch_id"> · ❄ {{ t('freezer') }}</span></span>
                <h3>{{ factsFor(entry)?.name }}</h3>
                <p><strong>{{ number(portionCalories(entry)) }} kcal</strong><span> · {{ number(entry.servings) }} {{ t('portions') }}</span></p>
              </div>
            </NuxtLink>
            <div class="meal-footer">
              <div class="diet-labels">
                <span v-if="factsFor(entry)?.gluten_free === 'yes'">{{ t('gfShort') }}</span><span v-if="factsFor(entry)?.lactose_free === 'yes'">{{ t('lfShort') }}</span>
              </div>
              <v-btn
                v-if="currentPlan && !currentPlan.consumed?.includes(entry.id!)"
                variant="tonal"
                size="small"
                :prepend-icon="mdiCheck"
                :disabled="busy"
                @click="consume(entry.id!)"
              >
                {{ t(entry.batch_id ? 'withdraw' : 'eaten') }}
              </v-btn>
              <span v-else-if="currentPlan" class="recorded-label"><v-icon :icon="mdiCheck" size="18" /> {{ t('recorded') }}</span>
              <v-btn v-else variant="text" size="small" :disabled="busy" @click="removeEntry(entry.id!)">
                {{ t('remove') }}
              </v-btn>
            </div>
          </article>
        </div>
        <div v-if="!entriesFor(selectedDay).length" class="empty-state">
          <v-icon :icon="mdiCalendarWeek" size="36" /><h3>{{ t('emptyDay') }}</h3><p>{{ t('empty') }}</p>
        </div>
        <div v-if="!currentPlan" class="draft-actions">
          <v-btn color="primary" :prepend-icon="mdiPlus" :disabled="busy" @click="newEntry">
            {{ t('add') }}
          </v-btn>
          <v-btn v-if="draft.entries.length" variant="outlined" :disabled="busy" @click="previewDraft">
            {{ t('preview') }} · {{ draft.entries.length }}
          </v-btn>
        </div>
        <p class="section-hint">
          {{ t('plannedOnly') }}
        </p>
      </section>
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
      <section v-if="tab === 'shopping'">
        <div class="shopping-progress" aria-live="polite">
          <strong>{{ checkedCount }} / {{ shoppingCount }}</strong><span>{{ t('itemsChecked') }}</span><v-progress-linear :model-value="shoppingCount ? checkedCount / shoppingCount * 100 : 0" color="primary" rounded height="5" />
        </div>
        <p class="section-hint">
          {{ t('shoppingHint') }}
        </p>
        <div class="shopping-list">
          <label v-for="item in summary?.shopping || []" :key="item.id" class="shopping-row" :class="{ checked: currentPlan?.checked_items?.includes(item.id) }">
            <input type="checkbox" :checked="currentPlan?.checked_items?.includes(item.id) || false" :disabled="!currentPlan || busy" @change="checkItem(item.id, ($event.target as HTMLInputElement).checked)">
            <span><strong>{{ item.name }}</strong><small>{{ t(item.state) }}</small></span><b>{{ number(item.grams) }} g</b>
          </label>
          <p v-if="!summary?.shopping.length" class="empty-state">
            {{ t('noShopping') }}
          </p>
        </div>
      </section>
      <PlannerPersonalPanel
        v-if="tab === 'goals' && personal"
        :personal="personal"
        :busy="busy"
        @save-profile="p => run(() => privateMutate('/profile', p, 'put'))"
        @propose="run(() => privateMutate('/goals/propose'))"
        @confirm="id => run(() => privateMutate(`/goals/${id}/confirm`))"
        @manual="g => run(() => privateMutate('/goals/manual', g))"
      />
    </template>
    <v-dialog v-model="entryDialog" scrollable class="planner-dialog" max-width="540">
      <v-card :title="t('add')" rounded="xl">
        <v-card-text>
          <v-alert v-if="!recipes.length" variant="tonal" class="mb-3">
            {{ t('needFacts') }}
          </v-alert>
          <v-select v-model="entryRecipe" :items="recipes" item-title="name" item-value="recipe_id" :label="t('recipe')" />
          <v-select v-model="entryPerson" :items="members" item-title="name" item-value="id" :label="t('person')" />
          <v-select v-model="entryDay" :items="days" :label="t('day')" />
          <v-select v-model="entryMeal" :items="mealOptions" :label="t('meal')" />
          <v-number-input
            v-model="entryServings"
            :precision="2"
            inputmode="decimal"
            :min="0.1"
            :step="0.5"
            :label="t('portions')"
          />
          <v-select v-model="entryBatch" :items="batchOptions" :label="t('source')" clearable />
        </v-card-text>
        <v-card-actions>
          <v-btn @click="entryDialog = false">
            {{ t('close') }}
          </v-btn><v-spacer /><v-btn color="primary" :disabled="!entryRecipe || !entryPerson || !entryServings || entryServings <= 0" @click="addEntry">
            {{ t('add') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="previewDialog" scrollable class="planner-dialog" max-width="600">
      <v-card :title="t('confirmTitle')" rounded="xl">
        <v-card-text>
          <p>{{ draft.entries.length }} {{ t('allocations') }}</p>
          <v-list><v-list-item v-for="entry in draft.entries" :key="entry.id" :title="factsFor(entry)?.name" :subtitle="`${shortDate(entry.day)} · ${t(entry.meal)} · ${personName(entry.user_id)} · ${number(entry.servings)} ${t('portions')}`" /></v-list>
          <p>{{ t('confirmHint') }}</p>
        </v-card-text><v-card-actions>
          <v-btn @click="previewDialog = false">
            {{ t('close') }}
          </v-btn><v-spacer /><v-btn color="primary" :loading="busy" @click="confirmDraft">
            {{ t('confirm') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
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
    <v-dialog v-model="cancelDialog" scrollable class="planner-dialog" max-width="440">
      <v-card :title="t('cancelPlan')">
        <v-card-text>{{ t('cancelHint') }}</v-card-text><v-card-actions>
          <v-btn @click="cancelDialog = false">
            {{ t('close') }}
          </v-btn><v-btn color="error" :disabled="busy" @click="cancelPlan">
            {{ t('cancelPlan') }}
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
    <v-dialog :model-value="pendingWeekShift !== null" class="planner-dialog" max-width="460" @update:model-value="value => { if (!value) pendingWeekShift = null; }">
      <v-card :title="t('unsavedDraft')">
        <v-card-text>{{ t('discardDraftHint') }}</v-card-text><v-card-actions>
          <v-btn @click="pendingWeekShift = null">
            {{ t('keepEditing') }}
          </v-btn><v-btn color="error" @click="shiftWeek(pendingWeekShift!)">
            {{ t('discardDraft') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { mdiCalendarWeek, mdiSnowflake, mdiPotSteamOutline, mdiCartOutline, mdiAccountCircleOutline, mdiRefresh, mdiChevronLeft, mdiChevronRight, mdiDotsHorizontal, mdiPlus, mdiCheck } from "@mdi/js";
import { addDays, format, startOfWeek, parseISO } from "date-fns";
import type { AllocationIn, PlanIn, BatchIn } from "~/lib/api/types/household-planner";
import { useHouseholdPlanner, type PlannerSummary } from "~/composables/use-household-planner";
import PlannerPersonalPanel from "~/components/Domain/Planner/PlannerPersonalPanel.vue";

const i18n = useI18n();
const auth = useMealieAuth();
const t = (key: string) => i18n.t(`household-planner.${key}`);
const { api, data, personal, members, busy, error, run, refresh, mutate, privateMutate } = useHouseholdPlanner();
const tab = ref("week");
const navigation = [
  { value: "week", label: "navWeek", icon: mdiCalendarWeek },
  { value: "freezer", label: "freezer", icon: mdiSnowflake },
  { value: "cook", label: "navCook", icon: mdiPotSteamOutline },
  { value: "shopping", label: "navShop", icon: mdiCartOutline },
  { value: "goals", label: "goals", icon: mdiAccountCircleOutline },
];
const today = format(new Date(), "yyyy-MM-dd");
const selectedDay = ref(today);
const showOverview = ref(false);
const stockSearch = ref("");
const showEmpty = ref(false);
const withdrawBatch = ref<string | null>(null);
const withdrawQuantity = ref(1);
const pendingWeekShift = ref<number | null>(null);
const person = ref("");
const week = ref(format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd"));
const days = computed(() => Array.from({ length: 7 }, (_, i) => format(addDays(parseISO(week.value), i), "yyyy-MM-dd")));
const shortDate = (day: string) => new Intl.DateTimeFormat(i18n.locale.value, { day: "numeric", month: "short" }).format(parseISO(day));
const weekLabel = computed(() => `${shortDate(week.value)} – ${shortDate(days.value[6]!)}`);
const currentPlan = computed(() => Object.values(data.value?.state.plans || {}).find(p => p.start === week.value));
const draft = reactive<PlanIn & { entries: AllocationIn[] }>({ start: week.value, entries: [] });
const summary = ref<PlannerSummary | null>(null);
const allEntries = computed(() => currentPlan.value?.entries || draft.entries);
const recipes = computed(() => Object.values(data.value?.state.facts || {}));
const batches = computed(() => Object.values(data.value?.state.batches || {}).sort((a, b) => a.frozen_on.localeCompare(b.frozen_on)));
const filteredBatches = computed(() => batches.value.filter(b => (showEmpty.value || b.remaining > 0) && `${b.facts.name} ${b.location}`.toLocaleLowerCase().includes((stockSearch.value || "").toLocaleLowerCase())));
const stockTotal = computed(() => batches.value.reduce((s, b) => s + b.remaining, 0));
const stockAvailable = computed(() => batches.value.reduce((s, b) => s + available(b.id!), 0));
const checkedCount = computed(() => (summary.value?.shopping || []).filter(i => currentPlan.value?.checked_items?.includes(i.id)).length);
const shoppingCount = computed(() => summary.value?.shopping.length || 0);
const selectedBatch = computed(() => batches.value.find(b => b.id === withdrawBatch.value));
const entryDialog = ref(false); const previewDialog = ref(false); const freezeDialog = ref(false); const cancelDialog = ref(false);
const entryRecipe = ref(""); const entryPerson = ref(""); const entryDay = ref(week.value); const entryMeal = ref<AllocationIn["meal"]>("dinner"); const entryServings = ref(1); const entryBatch = ref<string | null>(null);
const freezeRecipe = ref(""); const freezeServings = ref(1); const freezeLocation = ref(""); const freezeDate = ref(format(new Date(), "yyyy-MM-dd"));
const mealOptions = computed(() => ["breakfast", "lunch", "dinner", "snack"].map(value => ({ title: t(value), value })));
const batchOptions = computed(() => batches.value.filter(b => b.recipe_id === entryRecipe.value && available(b.id!) > 0).map(b => ({ title: `${b.frozen_on} · ${b.location} · ${available(b.id!)} ${t("portions")}`, value: b.id })));
const number = (v: number | null | undefined) => v == null ? "—" : new Intl.NumberFormat(i18n.locale.value, { maximumFractionDigits: 1 }).format(v);
const personName = (id: string) => members.value.find(m => m.id === id)?.name || "";
const dayLabel = (d: string) => new Intl.DateTimeFormat(i18n.locale.value, { weekday: "short" }).format(parseISO(d));
const mealOrder = ["breakfast", "lunch", "dinner", "snack"];
const entriesFor = (day: string) => allEntries.value.filter(e => e.day === day && (!person.value || e.user_id === person.value)).sort((a, b) => mealOrder.indexOf(a.meal) - mealOrder.indexOf(b.meal));
const dayTotal = (day: string) => summary.value?.days.find(d => d.day === day && d.user_id === person.value);
const factsFor = (e: AllocationIn) => e.batch_id ? data.value?.state.batches?.[e.batch_id]?.facts : currentPlan.value?.recipe_snapshots?.[e.recipe_id] || data.value?.state.facts?.[e.recipe_id];
function portionCalories(entry: AllocationIn) { const calories = factsFor(entry)?.per_serving.calories; return calories == null ? null : calories * entry.servings; }
function available(id: string) {
  const reserved = Object.values(data.value?.state.plans || {}).flatMap(p => (p.entries || []).filter(e => e.batch_id === id && !p.consumed?.includes(e.id!))).reduce((s, e) => s + e.servings, 0);
  return (data.value?.state.batches?.[id]?.remaining || 0) - reserved;
}
async function loadSummary() { summary.value = currentPlan.value?.id ? await api.read<PlannerSummary>(`/plans/${currentPlan.value.id}/summary`) : null; }
function shiftWeek(n: number) {
  const offset = days.value.indexOf(selectedDay.value);
  week.value = format(addDays(parseISO(week.value), n), "yyyy-MM-dd");
  selectedDay.value = days.value[Math.max(0, offset)]!;
  draft.start = week.value; draft.entries = []; draft.id = undefined; summary.value = null;
  pendingWeekShift.value = null;
  run(loadSummary);
}
function requestWeekShift(n: number) {
  if (draft.entries.length && !currentPlan.value) pendingWeekShift.value = n;
  else shiftWeek(n);
}
function selectDay(day: string) { selectedDay.value = day; showOverview.value = false; }
function changeTab(value: string) { tab.value = value; window.scrollTo({ top: 0, behavior: "instant" }); }
function removeEntry(id: string) { draft.entries = draft.entries.filter(e => e.id !== id); summary.value = null; }
async function refreshAll() { await refresh(); await loadSummary(); }
function newEntry() { entryPerson.value = person.value || members.value[0]?.id || ""; entryDay.value = selectedDay.value; entryBatch.value = null; entryDialog.value = true; }
function addEntry() { draft.entries.push({ id: crypto.randomUUID(), recipe_id: entryRecipe.value, user_id: entryPerson.value, day: entryDay.value, meal: entryMeal.value, servings: entryServings.value, batch_id: entryBatch.value }); entryDialog.value = false; summary.value = null; }
function previewDraft() { run(async () => { draft.id ||= crypto.randomUUID(); const r = await api.write<{ summary: PlannerSummary }>("/preview", draft, data.value!.revision); summary.value = r.summary; previewDialog.value = true; }); }
function confirmDraft() { run(async () => { await mutate("/confirm", draft); previewDialog.value = false; draft.entries = []; await loadSummary(); }); }
function consume(id: string) { run(async () => { await mutate(`/plans/${currentPlan.value!.id}/consume/${id}`, {}); await loadSummary(); }); }
function cancelPlan() { run(async () => { await mutate(`/plans/${currentPlan.value!.id}`, {}, "delete"); cancelDialog.value = false; summary.value = null; }); }
function askWithdraw(id: string) { withdrawQuantity.value = Math.min(1, available(id)); withdrawBatch.value = id; }
function withdraw() {
  if (!withdrawBatch.value || !withdrawQuantity.value) return;
  run(async () => { await mutate("/movements", { id: crypto.randomUUID(), batch_id: withdrawBatch.value, kind: "withdraw", servings: withdrawQuantity.value }); withdrawBatch.value = null; });
}
function freeze() { const payload: BatchIn = { id: crypto.randomUUID(), recipe_id: freezeRecipe.value, servings: freezeServings.value, frozen_on: freezeDate.value, location: freezeLocation.value }; run(async () => { await mutate("/batches", payload); freezeDialog.value = false; }); }
function checkItem(id: string, checked: boolean) { const list = new Set(currentPlan.value?.checked_items || []); if (checked) list.add(id); else list.delete(id); run(() => mutate(`/plans/${currentPlan.value!.id}/shopping`, [...list], "put")); }
watch(entryRecipe, () => { entryBatch.value = null; });
onMounted(() => run(async () => { await refresh(); person.value = members.value.find(m => m.id === auth.user.value?.id)?.id || members.value[0]?.id || ""; await loadSummary(); }));
</script>

<style scoped>
.planner-shell {
  --line: rgba(var(--v-theme-on-surface), 0.1);
  max-width: 1120px;
  padding: 18px 16px calc(96px + env(safe-area-inset-bottom));
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
.planner-navigation button,
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
.planner-navigation {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  padding: 6px 8px calc(6px + env(safe-area-inset-bottom));
  background: rgb(var(--v-theme-surface));
  border-top: 1px solid var(--line);
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.04);
}
.planner-navigation button {
  min-height: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  font-size: 0.66rem;
  font-weight: 600;
  border-radius: 14px;
  color: rgba(var(--v-theme-on-surface), 0.7);
  overflow-wrap: anywhere;
}
.planner-navigation button[aria-current] {
  color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.1);
}
.week-navigation {
  display: grid;
  grid-template-columns: 44px 1fr 44px;
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
.shopping-progress {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 10px;
  margin: 16px 0;
}
.shopping-progress strong {
  font-size: 1.5rem;
}
.shopping-progress span {
  font-size: 0.8rem;
  opacity: 0.65;
}
.shopping-progress .v-progress-linear {
  margin-top: 4px;
}
.shopping-list {
  border: 1px solid var(--line);
  border-radius: 18px;
  overflow: hidden;
}
.shopping-row {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 76px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
}
.shopping-row:last-child {
  border: 0;
}
.shopping-row input {
  width: 23px;
  height: 23px;
  flex-shrink: 0;
  accent-color: rgb(var(--v-theme-primary));
}
.shopping-row > span {
  flex: 1;
  min-width: 0;
}
.shopping-row strong {
  font-size: 0.9rem;
  display: block;
  overflow-wrap: anywhere;
}
.shopping-row small {
  display: block;
  font-size: 0.7rem;
  opacity: 0.6;
  margin-top: 3px;
}
.shopping-row b {
  font-size: 0.8rem;
  white-space: nowrap;
}
.shopping-row.checked {
  background: rgba(var(--v-theme-on-surface), 0.025);
}
.shopping-row.checked strong {
  text-decoration: line-through;
  opacity: 0.5;
}
@media (min-width: 900px) {
  .planner-shell {
    padding: 24px 28px 48px;
  }
  .planner-navigation {
    position: static;
    display: flex;
    border-top: 0;
    border-bottom: 1px solid var(--line);
    box-shadow: none;
    padding: 0 0 12px;
    gap: 8px;
    margin-bottom: 20px;
  }
  .planner-navigation button {
    flex-direction: row;
    gap: 8px;
    padding: 10px 18px;
    font-size: 0.8rem;
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
