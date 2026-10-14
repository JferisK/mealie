<template>
  <v-container class="planner-shell">
    <header class="planner-hero">
      <div>
        <span class="eyebrow">{{ t('eyebrow') }}</span>
        <h1>{{ t('title') }}</h1>
        <p>{{ t('subtitle') }}</p>
      </div>
      <v-btn variant="outlined" :loading="busy" @click="run(refresh)">
        {{ t('refresh') }}
      </v-btn>
    </header>
    <v-alert v-if="error" type="error" class="mb-4" closable @click:close="error = ''">
      {{ error }}
    </v-alert>
    <v-tabs v-model="tab" color="primary" class="mb-6" show-arrows>
      <v-tab value="week">
        {{ t('week') }}
      </v-tab>
      <v-tab value="freezer">
        {{ t('freezer') }}
      </v-tab>
      <v-tab value="cook">
        {{ t('cook') }}
      </v-tab>
      <v-tab value="shopping">
        {{ t('shopping') }}
      </v-tab>
      <v-tab value="goals">
        {{ t('goals') }}
      </v-tab>
    </v-tabs>
    <template v-if="data">
      <div v-if="['week', 'cook', 'shopping'].includes(tab)" class="planner-toolbar">
        <v-btn variant="text" :aria-label="t('previous')" @click="shiftWeek(-7)">
          ←
        </v-btn>
        <strong>{{ weekLabel }}</strong>
        <v-btn variant="text" :aria-label="t('next')" @click="shiftWeek(7)">
          →
        </v-btn>
        <v-select
          v-model="person"
          :items="members"
          item-title="name"
          item-value="id"
          :label="t('person')"
          hide-details
          density="compact"
          class="person-select"
        />
      </div>
      <section v-if="tab === 'week'">
        <div class="d-flex ga-3 flex-wrap mb-5">
          <v-btn color="primary" :disabled="busy || !!currentPlan" @click="newEntry">
            {{ t('add') }}
          </v-btn>
          <v-btn v-if="draft.entries.length && !currentPlan" variant="outlined" :disabled="busy" @click="previewDraft">
            {{ t('preview') }}
          </v-btn>
          <v-btn v-if="currentPlan" variant="text" color="error" :disabled="busy" @click="cancelDialog = true">
            {{ t('cancelPlan') }}
          </v-btn>
        </div>
        <v-alert v-if="!allEntries.length" variant="tonal" class="mb-5">
          {{ t('empty') }}
        </v-alert>
        <div class="week-grid">
          <article v-for="day in days" :key="day" class="day-card">
            <div class="day-heading">
              <span>{{ dayLabel(day) }}</span><small>{{ day.slice(8) }}.{{ day.slice(5, 7) }}.</small>
            </div>
            <div class="day-nutrition">
              <b>{{ number(dayTotal(day)?.nutrients.calories) }}</b> kcal <span>· {{ number(dayTotal(day)?.nutrients.protein) }} g {{ t('protein') }}</span>
            </div>
            <small v-if="dayTotal(day)" class="muted">{{ dayTotal(day)?.known_entries }}/{{ dayTotal(day)?.entries }} {{ t('complete') }}</small>
            <div v-for="entry in entriesFor(day)" :key="entry.id" class="meal-card">
              <img v-if="factsFor(entry)?.image" :src="`/api/media/recipes/${entry.recipe_id}/images/min-original.webp`" :alt="factsFor(entry)?.name" loading="lazy">
              <div class="meal-content">
                <span class="meal-label">{{ t(entry.meal) }}<span v-if="entry.batch_id"> · ❄</span></span>
                <h3><NuxtLink :to="`/g/${auth.user.value?.groupSlug}/r/${factsFor(entry)?.slug}`">{{ factsFor(entry)?.name }}</NuxtLink></h3>
                <p>{{ number(portionCalories(entry)) }} kcal</p>
                <p>{{ entry.servings }} {{ t('portions') }} · {{ personName(entry.user_id) }}</p>
                <div class="d-flex ga-1 flex-wrap">
                  <v-chip v-if="factsFor(entry)?.gluten_free === 'yes'" size="x-small">
                    {{ t('gf') }}
                  </v-chip>
                  <v-chip v-if="factsFor(entry)?.lactose_free === 'yes'" size="x-small">
                    {{ t('lf') }}
                  </v-chip>
                </div>
                <v-btn v-if="currentPlan && !currentPlan.consumed?.includes(entry.id!)" size="small" variant="text" :disabled="busy" @click="consume(entry.id!)">
                  {{ t('consumed') }}
                </v-btn>
                <small v-else-if="currentPlan" class="muted">✓ {{ t('recorded') }}</small>
                <v-btn v-else size="small" variant="text" @click="draft.entries = draft.entries.filter(e => e.id !== entry.id)">
                  {{ t('remove') }}
                </v-btn>
              </div>
            </div>
          </article>
        </div>
        <p class="muted mt-5">
          {{ t('plannedOnly') }}
        </p>
      </section>
      <section v-if="tab === 'freezer'">
        <div class="d-flex justify-space-between mb-5">
          <h2>{{ t('freezer') }}</h2><v-btn color="primary" @click="freezeDialog = true">
            {{ t('freeze') }}
          </v-btn>
        </div>
        <v-alert v-if="!batches.length" variant="tonal">
          {{ t('emptyFreezer') }}
        </v-alert>
        <div class="stock-grid">
          <v-card v-for="batch in batches" :key="batch.id" variant="outlined" rounded="xl">
            <v-card-title>{{ batch.facts.name }}</v-card-title>
            <v-card-text>
              <div class="stock-count">
                {{ number(batch.remaining) }} <small>{{ t('portions') }}</small>
              </div>
              <p>{{ number(available(batch.id!)) }} {{ t('available') }} · {{ batch.location || '—' }}</p>
              <p class="muted">
                {{ t('frozenOn') }} {{ batch.frozen_on }}
              </p>
              <p>{{ batch.facts.reheating_instructions }}</p>
              <v-btn class="mt-4" variant="tonal" :disabled="busy || available(batch.id!) < 1" @click="withdraw(batch.id!)">
                −1 {{ t('withdraw') }}
              </v-btn>
            </v-card-text>
          </v-card>
        </div>
      </section>
      <section v-if="tab === 'cook'">
        <h2 class="mb-2">
          {{ t('cook') }}
        </h2><p class="muted mb-5">
          {{ t('cookHint') }}
        </p>
        <v-list lines="two" rounded="xl">
          <v-list-item v-for="dish in summary?.cooking || []" :key="dish.recipe_id" :title="dish.name" :subtitle="`${number(dish.servings)} ${t('portions')}`">
            <template #append>
              <v-btn variant="tonal" @click="freezeRecipe = dish.recipe_id; freezeServings = dish.servings; freezeDialog = true">
                {{ t('freeze') }}
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
        <v-alert v-if="!summary?.cooking.length" variant="tonal">
          {{ t('noCooking') }}
        </v-alert>
      </section>
      <section v-if="tab === 'shopping'">
        <h2 class="mb-2">
          {{ t('shopping') }}
        </h2><p class="muted mb-5">
          {{ t('shoppingHint') }}
        </p>
        <v-card variant="outlined" rounded="xl">
          <v-checkbox
            v-for="item in summary?.shopping || []"
            :key="item.id"
            :model-value="currentPlan?.checked_items?.includes(item.id) || false"
            :disabled="!currentPlan || busy"
            :label="`${item.name} · ${item.grams} g (${item.state})`"
            hide-details
            class="px-4"
            @update:model-value="checkItem(item.id, !!$event)"
          />
          <v-card-text v-if="!summary?.shopping.length">
            {{ t('noShopping') }}
          </v-card-text>
        </v-card>
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
    <v-dialog v-model="entryDialog" max-width="540">
      <v-card :title="t('add')" rounded="xl">
        <v-card-text>
          <v-alert v-if="!recipes.length" variant="tonal" class="mb-3">
            {{ t('needFacts') }}
          </v-alert>
          <v-select v-model="entryRecipe" :items="recipes" item-title="name" item-value="recipe_id" :label="t('recipe')" />
          <v-select v-model="entryPerson" :items="members" item-title="name" item-value="id" :label="t('person')" />
          <v-select v-model="entryDay" :items="days" :label="t('day')" />
          <v-select v-model="entryMeal" :items="mealOptions" :label="t('meal')" />
          <v-number-input v-model="entryServings" :min="0.1" :step="0.5" :label="t('portions')" />
          <v-select v-model="entryBatch" :items="batchOptions" :label="t('source')" clearable />
        </v-card-text>
        <v-card-actions>
          <v-btn @click="entryDialog = false">
            {{ t('close') }}
          </v-btn><v-spacer /><v-btn color="primary" :disabled="!entryRecipe || !entryPerson" @click="addEntry">
            {{ t('add') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="previewDialog" max-width="600">
      <v-card :title="t('confirmTitle')" rounded="xl">
        <v-card-text>
          <p>{{ draft.entries.length }} {{ t('allocations') }}</p>
          <v-list><v-list-item v-for="dish in summary?.cooking" :key="dish.recipe_id" :title="dish.name" :subtitle="`${dish.servings} ${t('portions')}`" /></v-list>
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
    <v-dialog v-model="freezeDialog" max-width="500">
      <v-card :title="t('freeze')" rounded="xl">
        <v-card-text>
          <v-select v-model="freezeRecipe" :items="recipes" item-title="name" item-value="recipe_id" :label="t('recipe')" />
          <v-number-input v-model="freezeServings" :min="0.1" :step="0.5" :label="t('portions')" />
          <v-text-field v-model="freezeDate" type="date" :label="t('frozenOn')" />
          <v-text-field v-model="freezeLocation" :label="t('location')" />
        </v-card-text><v-card-actions>
          <v-btn @click="freezeDialog = false">
            {{ t('close') }}
          </v-btn><v-spacer /><v-btn color="primary" :disabled="!freezeRecipe || busy" @click="freeze">
            {{ t('save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="cancelDialog" max-width="440">
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
  </v-container>
</template>

<script setup lang="ts">
import { addDays, format, startOfWeek, parseISO } from "date-fns";
import type { AllocationIn, PlanIn, BatchIn } from "~/lib/api/types/household-planner";
import { useHouseholdPlanner, type PlannerSummary } from "~/composables/use-household-planner";
import PlannerPersonalPanel from "~/components/Domain/Planner/PlannerPersonalPanel.vue";

const i18n = useI18n();
const auth = useMealieAuth();
const t = (key: string) => i18n.t(`household-planner.${key}`);
const { api, data, personal, members, busy, error, run, refresh, mutate, privateMutate } = useHouseholdPlanner();
const tab = ref("week");
const person = ref("");
const week = ref(format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd"));
const days = computed(() => Array.from({ length: 7 }, (_, i) => format(addDays(parseISO(week.value), i), "yyyy-MM-dd")));
const weekLabel = computed(() => `${days.value[0]} – ${days.value[6]}`);
const currentPlan = computed(() => Object.values(data.value?.state.plans || {}).find(p => p.start === week.value));
const draft = reactive<PlanIn & { entries: AllocationIn[] }>({ start: week.value, entries: [] });
const summary = ref<PlannerSummary | null>(null);
const allEntries = computed(() => currentPlan.value?.entries || draft.entries);
const recipes = computed(() => Object.values(data.value?.state.facts || {}));
const batches = computed(() => Object.values(data.value?.state.batches || {}).sort((a, b) => a.frozen_on.localeCompare(b.frozen_on)));
const entryDialog = ref(false); const previewDialog = ref(false); const freezeDialog = ref(false); const cancelDialog = ref(false);
const entryRecipe = ref(""); const entryPerson = ref(""); const entryDay = ref(week.value); const entryMeal = ref<AllocationIn["meal"]>("dinner"); const entryServings = ref(1); const entryBatch = ref<string | null>(null);
const freezeRecipe = ref(""); const freezeServings = ref(1); const freezeLocation = ref(""); const freezeDate = ref(format(new Date(), "yyyy-MM-dd"));
const mealOptions = computed(() => ["breakfast", "lunch", "dinner", "snack"].map(value => ({ title: t(value), value })));
const batchOptions = computed(() => batches.value.filter(b => b.recipe_id === entryRecipe.value && available(b.id!) > 0).map(b => ({ title: `${b.frozen_on} · ${b.location} · ${available(b.id!)} ${t("portions")}`, value: b.id })));
const number = (v: number | null | undefined) => v == null ? "—" : Math.round(v * 10) / 10;
const personName = (id: string) => members.value.find(m => m.id === id)?.name || "";
const dayLabel = (d: string) => new Intl.DateTimeFormat(i18n.locale.value, { weekday: "short" }).format(parseISO(d));
const entriesFor = (day: string) => allEntries.value.filter(e => e.day === day && (!person.value || e.user_id === person.value));
const dayTotal = (day: string) => summary.value?.days.find(d => d.day === day && d.user_id === person.value);
const factsFor = (e: AllocationIn) => e.batch_id ? data.value?.state.batches?.[e.batch_id]?.facts : currentPlan.value?.recipe_snapshots?.[e.recipe_id] || data.value?.state.facts?.[e.recipe_id];
function portionCalories(entry: AllocationIn) { const calories = factsFor(entry)?.per_serving.calories; return calories == null ? null : calories * entry.servings; }
function available(id: string) {
  const reserved = Object.values(data.value?.state.plans || {}).flatMap(p => (p.entries || []).filter(e => e.batch_id === id && !p.consumed?.includes(e.id!))).reduce((s, e) => s + e.servings, 0);
  return (data.value?.state.batches?.[id]?.remaining || 0) - reserved;
}
async function loadSummary() { summary.value = currentPlan.value?.id ? await api.read<PlannerSummary>(`/plans/${currentPlan.value.id}/summary`) : null; }
function shiftWeek(n: number) { week.value = format(addDays(parseISO(week.value), n), "yyyy-MM-dd"); draft.start = week.value; draft.entries = []; draft.id = undefined; summary.value = null; run(loadSummary); }
function newEntry() { entryPerson.value = person.value || members.value[0]?.id || ""; entryDay.value = week.value; entryBatch.value = null; entryDialog.value = true; }
function addEntry() { draft.entries.push({ id: crypto.randomUUID(), recipe_id: entryRecipe.value, user_id: entryPerson.value, day: entryDay.value, meal: entryMeal.value, servings: entryServings.value, batch_id: entryBatch.value }); entryDialog.value = false; summary.value = null; }
function previewDraft() { run(async () => { draft.id ||= crypto.randomUUID(); const r = await api.write<{ summary: PlannerSummary }>("/preview", draft, data.value!.revision); summary.value = r.summary; previewDialog.value = true; }); }
function confirmDraft() { run(async () => { await mutate("/confirm", draft); previewDialog.value = false; draft.entries = []; await loadSummary(); }); }
function consume(id: string) { run(async () => { await mutate(`/plans/${currentPlan.value!.id}/consume/${id}`, {}); await loadSummary(); }); }
function cancelPlan() { run(async () => { await mutate(`/plans/${currentPlan.value!.id}`, {}, "delete"); cancelDialog.value = false; summary.value = null; }); }
function withdraw(id: string) { run(() => mutate("/movements", { id: crypto.randomUUID(), batch_id: id, kind: "withdraw", servings: 1 })); }
function freeze() { const payload: BatchIn = { id: crypto.randomUUID(), recipe_id: freezeRecipe.value, servings: freezeServings.value, frozen_on: freezeDate.value, location: freezeLocation.value }; run(async () => { await mutate("/batches", payload); freezeDialog.value = false; }); }
function checkItem(id: string, checked: boolean) { const list = new Set(currentPlan.value?.checked_items || []); if (checked) list.add(id); else list.delete(id); run(() => mutate(`/plans/${currentPlan.value!.id}/shopping`, [...list], "put")); }
watch(entryRecipe, () => { entryBatch.value = null; });
onMounted(() => run(async () => { await refresh(); person.value = members.value[0]?.id || ""; await loadSummary(); }));
</script>

<style scoped>
.planner-shell {
  max-width: 1500px;
  padding: 32px 24px 60px;
}
.planner-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
}
.eyebrow {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: rgb(var(--v-theme-primary));
  font-weight: 700;
}
h1 {
  font-size: clamp(1.9rem, 4vw, 3rem);
  letter-spacing: -0.05em;
  margin: 8px 0;
}
.planner-hero p,
.muted {
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.65;
}
.planner-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.person-select {
  max-width: 240px;
  min-width: 150px;
  margin-left: auto;
}
.week-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
}
.day-card {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.1);
  border-radius: 18px;
  padding: 12px;
  min-height: 260px;
}
.day-heading {
  display: flex;
  justify-content: space-between;
  font-weight: 700;
}
.day-heading small {
  opacity: 0.5;
}
.day-nutrition {
  font-size: 0.8rem;
  margin-top: 12px;
}
.day-nutrition b {
  font-size: 1.25rem;
}
.day-nutrition span {
  display: block;
}
.meal-card {
  border-radius: 12px;
  overflow: hidden;
  background: rgba(var(--v-theme-primary), 0.045);
  margin-top: 18px;
}
.meal-card img {
  width: 100%;
  height: 115px;
  object-fit: cover;
}
.meal-content {
  padding: 12px;
}
.meal-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.65;
}
.meal-content h3 {
  font-size: 0.95rem;
  line-height: 1.35;
  margin: 6px 0;
}
.meal-content p {
  font-size: 0.75rem;
  margin-bottom: 8px;
}
.stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 18px;
}
.stock-count {
  font-size: 2.5rem;
  font-weight: 600;
  letter-spacing: -0.06em;
}
.stock-count small {
  font-size: 0.9rem;
  letter-spacing: 0;
  font-weight: 400;
}
@media (max-width: 1150px) {
  .week-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 650px) {
  .planner-shell {
    padding: 20px 12px;
  }
  .planner-hero {
    align-items: flex-start;
  }
  .week-grid {
    grid-template-columns: 1fr;
  }
  .day-card {
    min-height: 100px;
    padding: 18px;
  }
  .meal-card {
    display: flex;
  }
  .meal-card img {
    width: 105px;
    min-height: 145px;
    height: auto;
  }
  .person-select {
    max-width: none;
    width: 100%;
  }
}
</style>
