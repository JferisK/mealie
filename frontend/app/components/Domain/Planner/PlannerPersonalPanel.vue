<template>
  <div class="goals">
    <section class="goals-hero" :class="{ 'is-empty': !active }">
      <span class="goals-hero__label">{{ t('dailyGoal') }}</span>
      <template v-if="active">
        <p class="goals-hero__value">
          <strong>{{ number(active.goals.calories) }}</strong> kcal
          <span class="goals-hero__sep" aria-hidden="true">·</span>
          <strong>{{ number(active.goals.protein) }}</strong> g {{ t('protein') }}
        </p>
        <p v-if="weekAverage" class="goals-hero__week">
          {{ t('plannedThisWeek') }}: Ø {{ number(weekAverage.calories) }} kcal · {{ number(weekAverage.protein) }} g
          <span :class="weekDeltaClass">({{ weekDelta }})</span>
        </p>
        <p class="goals-hero__since">
          {{ t('activeSince') }} {{ dateLabel(active.confirmed_at) }}
        </p>
      </template>
      <p v-else class="goals-hero__value">
        {{ t('noGoalYet') }}
      </p>
    </section>

    <v-alert v-if="personal.review_due && active" variant="tonal" type="info" class="mb-6">
      {{ t('reviewDue') }}
    </v-alert>

    <section class="calc">
      <h2>{{ t('calculator') }}</h2>

      <div class="calc-block">
        <div class="calc-weight">
          <div>
            <span class="calc-label">{{ t('currentWeight') }}</span>
            <p v-if="latestWeight" class="calc-weight__value">
              <strong>{{ number(latestWeight.value, 1) }} kg</strong>
              <span>{{ latestWeight.source === 'manual' ? t('sourceManual') : t('sourceHealth') }}, {{ dateLabel(latestWeight.at) }}</span>
            </p>
            <p v-else class="calc-weight__value">
              {{ t('noWeight') }}
            </p>
          </div>
          <div class="calc-weight__entry">
            <v-number-input
              v-model="newWeight"
              :precision="1"
              :min="20"
              :max="500"
              :step="0.1"
              inputmode="decimal"
              :label="t('weighedToday')"
              suffix="kg"
              density="comfortable"
              variant="outlined"
              hide-details
              control-variant="hidden"
            />
            <v-btn variant="tonal" :disabled="busy || !newWeight" @click="saveWeight">
              {{ t('save') }}
            </v-btn>
          </div>
        </div>
      </div>

      <div class="calc-grid">
        <v-number-input
          v-model="profile.height_cm"
          :precision="0"
          :min="100"
          :max="250"
          inputmode="numeric"
          :label="t('height')"
          suffix="cm"
          variant="outlined"
          density="comfortable"
          control-variant="hidden"
        />
        <v-text-field v-model="profile.birth_date" type="date" :label="t('birthDate')" variant="outlined" density="comfortable" />
        <v-select
          v-model="profile.equation_sex"
          :items="[{ title: t('male'), value: 'male' }, { title: t('female'), value: 'female' }]"
          :label="t('equationSex')"
          variant="outlined"
          density="comfortable"
        />
      </div>

      <fieldset class="calc-choice">
        <legend>{{ t('activity') }}</legend>
        <button
          v-for="a in activityLevels"
          :key="a.value"
          type="button"
          :aria-pressed="profile.activity_factor === a.value"
          @click="profile.activity_factor = a.value"
        >
          <strong>{{ a.title }}</strong>
          <span>{{ a.hint }}</span>
        </button>
      </fieldset>

      <fieldset class="calc-choice calc-choice--compact">
        <legend>{{ t('deficit') }}</legend>
        <button
          v-for="d in deficits"
          :key="d"
          type="button"
          :aria-pressed="profile.deficit_kcal === d"
          @click="profile.deficit_kcal = d"
        >
          <strong>{{ d === 0 ? t('maintain') : `−${d} kcal` }}</strong>
          <span>{{ d === 0 ? t('maintainHint') : `≈ ${number(d * 7 / 7700, 1)} kg ${t('perWeek')}` }}</span>
        </button>
      </fieldset>

      <div class="calc-grid">
        <v-number-input
          v-model="profile.protein_reference_kg"
          :precision="0"
          :min="30"
          :max="250"
          inputmode="numeric"
          :label="t('referenceWeight')"
          :hint="t('referenceWeightHint')"
          persistent-hint
          suffix="kg"
          variant="outlined"
          density="comfortable"
          control-variant="hidden"
        />
        <fieldset class="calc-choice calc-choice--compact calc-choice--inline">
          <legend>{{ t('proteinFactor') }}</legend>
          <button
            v-for="f in proteinFactors"
            :key="f"
            type="button"
            :aria-pressed="profile.protein_g_per_kg === f"
            @click="profile.protein_g_per_kg = f"
          >
            <strong>{{ number(f, 1) }} g/kg</strong>
          </button>
        </fieldset>
      </div>

      <div class="calc-result" aria-live="polite">
        <template v-if="calc">
          <div class="calc-step">
            <span>{{ t('restingRate') }}</span>
            <strong>{{ number(calc.resting) }} kcal</strong>
          </div>
          <div class="calc-step">
            <span>× {{ t('activityShort') }} {{ number(profile.activity_factor, 3) }}</span>
            <strong>{{ number(calc.total) }} kcal</strong>
          </div>
          <div class="calc-step">
            <span>− {{ t('deficitShort') }}</span>
            <strong>{{ number(profile.deficit_kcal) }} kcal</strong>
          </div>
          <div class="calc-step calc-step--total">
            <span>{{ t('dailyGoal') }}</span>
            <strong>{{ number(calc.target) }} kcal · {{ number(calc.protein) }} g {{ t('protein') }}</strong>
          </div>
          <p class="calc-note">
            {{ t('formulaNote') }}
          </p>
        </template>
        <p v-else class="calc-note">
          {{ t('calcMissing') }}
        </p>
        <v-btn color="primary" size="large" :disabled="busy || !calc" :loading="busy" @click="emit('adopt', { ...profile })">
          {{ t('adoptGoal') }}
        </v-btn>
      </div>
    </section>

    <details class="goals-more">
      <summary>{{ t('advanced') }}</summary>
      <div class="goals-more__body">
        <h3>{{ t('mealPreferences') }}</h3>
        <v-checkbox v-model="profile.gluten_free" :label="t('gf')" hide-details density="compact" />
        <v-checkbox v-model="profile.lactose_free" :label="t('lf')" hide-details density="compact" />
        <v-checkbox v-model="profile.avoid_traces" :label="t('traces')" hide-details density="compact" />
        <v-combobox
          v-model="profile.dislikes"
          :label="t('dislikes')"
          chips
          multiple
          closable-chips
          variant="outlined"
          class="mt-3"
        />
        <v-btn variant="tonal" :disabled="busy" @click="emit('saveProfile', { ...profile })">
          {{ t('save') }}
        </v-btn>

        <h3 class="mt-6">
          {{ t('manualTargets') }}
        </h3>
        <div class="calc-grid">
          <v-number-input
            v-model="manual.calories"
            :precision="0"
            :min="800"
            inputmode="numeric"
            label="kcal"
            variant="outlined"
            density="comfortable"
            control-variant="hidden"
          />
          <v-number-input
            v-model="manual.protein"
            :precision="0"
            :min="20"
            inputmode="numeric"
            :label="`${t('protein')} (g)`"
            variant="outlined"
            density="comfortable"
            control-variant="hidden"
          />
        </div>
        <v-btn variant="tonal" :disabled="busy || !manual.calories || !manual.protein" @click="emit('manual', { ...manual })">
          {{ t('adoptGoal') }}
        </v-btn>
        <p class="calc-note mt-4">
          {{ t('privateHint') }}
        </p>
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import type { GoalsIn, PersonalOut, ProfileIn } from "~/lib/api/types/household-planner";

const props = defineProps<{
  personal: PersonalOut;
  busy: boolean;
  weekAverage?: { calories: number; protein: number } | null;
}>();
const emit = defineEmits<{
  saveProfile: [profile: ProfileIn];
  adopt: [profile: ProfileIn];
  addWeight: [kg: number];
  manual: [goals: GoalsIn];
}>();
const i18n = useI18n();
const t = (key: string) => i18n.t(`household-planner.${key}`);

const activityLevels = computed(() => [
  { value: 1.2, title: t("activitySitting"), hint: t("activitySittingHint") },
  { value: 1.375, title: t("activityLight"), hint: t("activityLightHint") },
  { value: 1.55, title: t("activityActive"), hint: t("activityActiveHint") },
  { value: 1.725, title: t("activityVery"), hint: t("activityVeryHint") },
]);
const deficits = [0, 250, 400, 500];
const proteinFactors = [1.2, 1.6, 2.0];

const profile = ref<ProfileIn>({ ...props.personal.state.profile });
watch(() => props.personal.state.profile, (p) => { profile.value = { ...p }; });
const active = computed(() => props.personal.state.active);
const manual = ref<GoalsIn>({
  calories: active.value?.goals.calories || 2000,
  protein: active.value?.goals.protein || 120,
});
const newWeight = ref<number | null>(null);

const number = (v: number | null | undefined, digits = 0) => v == null
  ? "—"
  : new Intl.NumberFormat(i18n.locale.value, { maximumFractionDigits: digits }).format(v);
const dateLabel = (iso?: string | null) => iso
  ? new Intl.DateTimeFormat(i18n.locale.value, { day: "numeric", month: "short" }).format(new Date(iso))
  : "";

const weights = computed(() => Object.values(props.personal.state.observations || {})
  .filter(o => o.kind === "weight_kg")
  .sort((a, b) => b.at.localeCompare(a.at)));
const latestWeight = computed(() => weights.value[0]);

// Same rule as the server: mean of the last 7 days, otherwise the latest value within 14 days.
const formulaWeight = computed(() => {
  const now = Date.now();
  const day = 86_400_000;
  const recent = weights.value.filter(o => now - new Date(o.at).getTime() < 7 * day);
  if (recent.length) return recent.reduce((s, o) => s + o.value, 0) / recent.length;
  return weights.value.find(o => now - new Date(o.at).getTime() < 14 * day)?.value ?? null;
});

const calc = computed(() => {
  const p = profile.value;
  const weight = formulaWeight.value;
  if (!weight || !p.height_cm || !p.birth_date || !p.equation_sex || !p.protein_reference_kg) return null;
  const birth = new Date(p.birth_date);
  const now = new Date();
  const age = now.getFullYear() - birth.getFullYear() - (now < new Date(now.getFullYear(), birth.getMonth(), birth.getDate()) ? 1 : 0);
  if (age < 18) return null;
  const resting = 10 * weight + 6.25 * p.height_cm - 5 * age + (p.equation_sex === "male" ? 5 : -161);
  const total = resting * (p.activity_factor ?? 1.4);
  return {
    resting,
    total,
    target: total - (p.deficit_kcal ?? 0),
    protein: p.protein_reference_kg * (p.protein_g_per_kg ?? 1.2),
  };
});

const weekDelta = computed(() => {
  if (!props.weekAverage || !active.value) return "";
  const diff = props.weekAverage.calories - active.value.goals.calories;
  return `${diff > 0 ? "+" : "−"}${number(Math.abs(diff))} kcal`;
});
const weekDeltaClass = computed(() => {
  if (!props.weekAverage || !active.value) return "";
  return Math.abs(props.weekAverage.calories - active.value.goals.calories) <= 150 ? "is-good" : "is-off";
});

function saveWeight() {
  if (!newWeight.value) return;
  emit("addWeight", newWeight.value);
  newWeight.value = null;
}
</script>

<style scoped>
.goals {
  --g-line: rgba(var(--v-theme-on-surface), 0.09);
  --g-soft: rgba(var(--v-theme-on-surface), 0.62);
  max-width: 760px;
}

.goals-hero {
  padding: 22px 24px;
  margin-bottom: 20px;
  border-radius: 18px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}

.goals-hero.is-empty {
  background: rgba(var(--v-theme-primary), 0.08);
  color: rgb(var(--v-theme-on-surface));
}

.goals-hero__label {
  font-size: 0.85rem;
  opacity: 0.85;
}

.goals-hero__value {
  margin-top: 4px;
  font-size: 1.15rem;
}

.goals-hero__value strong {
  font-size: clamp(2rem, 1.6rem + 1.6vw, 2.6rem);
  font-weight: 750;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.goals-hero__sep {
  margin: 0 8px;
  opacity: 0.6;
}

.goals-hero__week,
.goals-hero__since {
  margin-top: 6px;
  font-size: 0.88rem;
  opacity: 0.9;
}

.goals-hero__week .is-good {
  font-weight: 650;
}

.goals-hero__week .is-off {
  font-weight: 650;
  text-decoration: underline;
}

.calc {
  padding: 22px 24px;
  border: 1px solid var(--g-line);
  border-radius: 18px;
  background: rgb(var(--v-theme-surface));
}

.calc h2 {
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 16px;
}

.calc-label,
legend {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--g-soft);
}

.calc-block {
  padding-bottom: 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--g-line);
}

.calc-weight {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: space-between;
  align-items: flex-end;
}

.calc-weight__value {
  display: flex;
  flex-direction: column;
  margin-top: 2px;
}

.calc-weight__value strong {
  font-size: 1.6rem;
  letter-spacing: -0.02em;
}

.calc-weight__value span {
  font-size: 0.82rem;
  color: var(--g-soft);
}

.calc-weight__entry {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 260px;
}

.calc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 12px;
}

.calc-choice {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
  margin: 6px 0 20px;
  border: 0;
  padding: 0;
}

.calc-choice legend {
  margin-bottom: 8px;
}

.calc-choice button {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border: 1px solid var(--g-line);
  border-radius: 12px;
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.calc-choice button span {
  font-size: 0.78rem;
  color: var(--g-soft);
  line-height: 1.3;
}

.calc-choice button[aria-pressed="true"] {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.08);
  box-shadow: inset 0 0 0 1px rgb(var(--v-theme-primary));
}

.calc-choice button:focus-visible,
summary:focus-visible {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.calc-choice--compact {
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
}

.calc-choice--inline {
  margin: 0;
}

.calc-result {
  margin-top: 8px;
  padding-top: 18px;
  border-top: 1px solid var(--g-line);
}

.calc-step {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  font-variant-numeric: tabular-nums;
}

.calc-step span {
  color: var(--g-soft);
}

.calc-step--total {
  margin-top: 6px;
  padding-top: 12px;
  border-top: 1px dashed var(--g-line);
  font-size: 1.1rem;
}

.calc-step--total span {
  color: rgb(var(--v-theme-on-surface));
  font-weight: 650;
}

.calc-step--total strong {
  color: rgb(var(--v-theme-primary));
}

.calc-note {
  margin: 10px 0 16px;
  font-size: 0.8rem;
  color: var(--g-soft);
}

.goals-more {
  margin-top: 20px;
  border-top: 1px solid var(--g-line);
}

.goals-more summary {
  padding: 16px 0;
  font-weight: 650;
  cursor: pointer;
}

.goals-more__body h3 {
  font-size: 0.95rem;
  margin-bottom: 8px;
}

@media (max-width: 600px) {
  .goals-hero,
  .calc {
    padding: 18px 16px;
  }

  .calc-weight__entry {
    min-width: 0;
    width: 100%;
  }
}
</style>
