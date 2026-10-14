<template>
  <div class="personal-grid">
    <div>
      <v-card variant="tonal" rounded="xl" :title="t('activeGoals')" class="mb-5">
        <v-card-text v-if="personal.state.active">
          <h2>{{ personal.state.active.goals.calories }} kcal · {{ personal.state.active.goals.protein }} g {{ t('protein') }}</h2><p>{{ personal.state.active.confirmed_at?.slice(0, 10) }}</p>
        </v-card-text>
        <v-card-text v-else>
          {{ t('noGoals') }}
        </v-card-text>
      </v-card>
      <v-alert v-if="personal.review_due" variant="tonal" class="mb-5">
        {{ t('reviewDue') }}
      </v-alert>
      <v-btn color="primary" :disabled="busy" class="mb-5" @click="emit('propose')">
        {{ t('recalculate') }}
      </v-btn>
      <v-card v-for="goal in proposals" :key="goal.id" variant="outlined" rounded="xl" class="mb-5">
        <v-card-title>{{ goal.goals.calories }} kcal · {{ goal.goals.protein }} g {{ t('protein') }}</v-card-title>
        <v-card-text>
          <p>{{ goal.explanation }}</p><details class="mt-3">
            <summary>{{ t('inputs') }}</summary><dl>
              <template v-for="(value, key) in goal.inputs" :key="key">
                <dt>{{ key }}</dt><dd>{{ value }}</dd>
              </template>
            </dl>
          </details>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" :disabled="busy" @click="emit('confirm', goal.id!)">
            {{ t('confirm') }}
          </v-btn>
        </v-card-actions>
      </v-card>
      <details class="manual-settings">
        <summary>{{ t('manualTargets') }}</summary><v-card variant="outlined" rounded="xl" :title="t('manualGoals')">
          <v-card-text>
            <v-number-input v-model="manual.calories" :precision="2" inputmode="decimal" label="kcal" :min="1" /><v-number-input v-model="manual.protein" :precision="2" inputmode="decimal" :label="`${t('protein')} (g)`" :min="1" /><v-btn variant="tonal" :disabled="busy" @click="emit('manual', manual)">
              {{ t('preview') }}
            </v-btn>
          </v-card-text>
        </v-card>
      </details>
    </div>
    <details class="profile-settings">
      <summary>{{ t('profileSettings') }}</summary>
      <v-card variant="outlined" rounded="xl" :title="t('profile')">
        <v-card-text>
          <p class="mb-5 text-medium-emphasis">
            {{ t('privateHint') }}
          </p>
          <v-text-field v-model="profile.birth_date" type="date" :label="t('birthDate')" />
          <v-number-input
            v-model="profile.height_cm"
            :precision="2"
            inputmode="decimal"
            :label="t('height')"
            :min="100"
            :max="250"
          />
          <v-select v-model="profile.equation_sex" :items="[{ title: t('male'), value: 'male' }, { title: t('female'), value: 'female' }]" :label="t('equationSex')" />
          <v-number-input
            v-model="profile.activity_factor"
            :precision="2"
            inputmode="decimal"
            :label="t('activity')"
            :min="1.2"
            :max="2.4"
            :step="0.1"
          />
          <v-number-input
            v-model="profile.deficit_kcal"
            :precision="2"
            inputmode="decimal"
            :label="t('deficit')"
            :min="0"
            :max="750"
            :step="50"
          />
          <v-number-input v-model="profile.protein_reference_kg" :precision="2" inputmode="decimal" :label="t('referenceWeight')" :min="1" />
          <v-number-input
            v-model="profile.protein_g_per_kg"
            :precision="2"
            inputmode="decimal"
            :label="t('proteinFactor')"
            :min="0.8"
            :max="2.2"
            :step="0.1"
          />
          <v-checkbox v-model="profile.gluten_free" :label="t('gf')" hide-details />
          <v-checkbox v-model="profile.lactose_free" :label="t('lf')" hide-details />
          <v-checkbox v-model="profile.avoid_traces" :label="t('traces')" hide-details />
          <v-combobox v-model="profile.dislikes" :label="t('dislikes')" chips multiple class="mt-4" />
          <v-btn color="primary" :disabled="busy" @click="emit('saveProfile', profile)">
            {{ t('save') }}
          </v-btn>
        </v-card-text>
      </v-card>
    </details>
  </div>
</template>

<script setup lang="ts">
import type { PersonalOut, ProfileIn, GoalsIn } from "~/lib/api/types/household-planner";

const props = defineProps<{ personal: PersonalOut; busy: boolean }>();
const emit = defineEmits<{ saveProfile: [profile: ProfileIn]; propose: []; confirm: [id: string]; manual: [goals: GoalsIn] }>();
const i18n = useI18n();
const t = (key: string) => i18n.t(`household-planner.${key}`);
const profile = ref<ProfileIn>({ ...props.personal.state.profile });
const manual = ref<GoalsIn>({ calories: props.personal.state.active?.goals.calories || 2000, protein: props.personal.state.active?.goals.protein || 100 });
const proposals = computed(() => [...(props.personal.state.revisions || [])].filter(g => !g.confirmed_at).reverse());
watch(() => props.personal.state.profile, (p) => { profile.value = { ...p }; });
</script>

<style scoped>
.personal-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 24px;
  max-width: 720px;
}
dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  font-size: 0.85rem;
  gap: 8px;
  margin-top: 12px;
}
summary {
  min-height: 52px;
  padding: 14px 0;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
}
summary:focus-visible {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: 3px;
}
:deep(.v-card-title) {
  white-space: normal;
  font-size: 1.1rem;
  line-height: 1.5;
}
:deep(.v-btn) {
  min-height: 44px;
  white-space: normal;
  height: auto;
  padding-top: 10px;
  padding-bottom: 10px;
  letter-spacing: 0;
}
:deep(.v-card-text h2) {
  font-size: 1.35rem;
  line-height: 1.5;
}
:deep(.v-label) {
  white-space: normal;
}
.profile-settings,
.manual-settings {
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.1);
}
dt,
dd {
  overflow-wrap: anywhere;
  min-width: 0;
}
</style>
