<template>
  <div class="pi">
    <div class="pi-toolbar">
      <PlannerWeekNav v-model="week" :disabled="busy" />
      <v-btn color="primary" variant="flat" :prepend-icon="mdiLightbulbOnOutline" :disabled="busy || !data" @click="openPicker">
        {{ t('proposeIdea') }}
      </v-btn>
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
    <v-progress-linear v-if="busy && !data" indeterminate />

    <div v-if="data && !ideas.length" class="fork-empty">
      <v-icon :icon="mdiLightbulbOutline" size="32" />
      <strong>{{ t('noIdeas') }}</strong>
      <p>{{ t('noIdeasHint') }}</p>
      <v-btn color="primary" variant="tonal" :prepend-icon="mdiLightbulbOnOutline" :disabled="busy" @click="openPicker">
        {{ t('proposeIdea') }}
      </v-btn>
    </div>

    <ol v-else class="pi-list">
      <li v-for="idea in ideas" :key="idea.id" class="pi-card" :class="{ 'is-planned': planned(idea.recipe_id) }">
        <NuxtLink :to="recipeLink(idea.slug)" class="pi-card__media">
          <img :src="imageFor(idea.recipe_id)" alt="" loading="lazy" @error="hideImage">
        </NuxtLink>
        <div class="pi-card__body">
          <div class="pi-card__head">
            <NuxtLink :to="recipeLink(idea.slug)" class="pi-card__title">
              {{ idea.name }}
            </NuxtLink>
            <v-btn
              :icon="mdiClose"
              size="small"
              variant="text"
              class="pi-card__remove"
              :aria-label="`${t('remove')}: ${idea.name}`"
              :disabled="busy"
              @click="remove(idea.id!)"
            />
          </div>
          <p class="pi-card__meta">
            <template v-if="facts(idea.recipe_id)">
              {{ number(facts(idea.recipe_id)?.per_serving.calories) }} kcal · {{ number(facts(idea.recipe_id)?.per_serving.protein) }} g {{ t('protein') }}
            </template>
            <template v-else>
              {{ t('noFactsShort') }}
            </template>
            · {{ t('proposedBy') }} {{ memberName(idea.proposed_by) }}
          </p>
          <p v-if="idea.note" class="pi-card__note">
            „{{ idea.note }}“
          </p>
          <div class="pi-card__actions">
            <button
              type="button"
              class="pi-like"
              :aria-pressed="liked(idea)"
              :disabled="busy"
              :aria-label="t('like')"
              @click="toggleLike(idea.id!)"
            >
              <v-icon :icon="liked(idea) ? mdiThumbUp : mdiThumbUpOutline" size="18" />
              <span>{{ idea.likes?.length || 0 }}</span>
            </button>
            <span class="pi-likers">
              <span v-for="id in idea.likes" :key="id" class="fork-person" :style="{ '--c': person(id)?.color }" :title="memberName(id)">{{ person(id)?.label || "?" }}</span>
            </span>
            <v-spacer />
            <span v-if="planned(idea.recipe_id)" class="pi-planned"><v-icon :icon="mdiCheck" size="16" /> {{ t('planned') }}</span>
            <v-btn
              v-else
              size="small"
              variant="tonal"
              color="primary"
              :disabled="!facts(idea.recipe_id)"
              :title="facts(idea.recipe_id) ? '' : t('needFactsShort')"
              :to="{ path: '/household/portions', query: { week, plan: idea.recipe_id } }"
            >
              {{ t('toWeekPlan') }}
            </v-btn>
          </div>
        </div>
      </li>
    </ol>

    <PlannerSheet v-model="dialog" fullscreen max-width="640" :title="t('proposeIdea')">
      <v-text-field
        v-model="note"
        :label="t('ideaNote')"
        variant="outlined"
        density="comfortable"
        hide-details
        class="mb-3"
        maxlength="500"
      />
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
      <v-progress-linear v-if="loadingRecipes" indeterminate class="mb-3" />
      <div class="pi-picklist">
        <button
          v-for="r in filteredRecipes"
          :key="r.id"
          type="button"
          class="pi-pick"
          :disabled="busy"
          @click="propose(r.id!)"
        >
          <img :src="imageFor(r.id!)" alt="" loading="lazy" @error="hideImage">
          <span>
            <strong>{{ r.name }}</strong>
            <small v-if="facts(r.id!)">{{ number(facts(r.id!)?.per_serving.calories) }} kcal</small>
            <small v-else>{{ t('noFactsShort') }}</small>
          </span>
        </button>
      </div>
      <p v-if="!loadingRecipes && !filteredRecipes.length" class="pi-card__meta mt-2">
        {{ t('noDishMatches') }}
      </p>
    </PlannerSheet>
  </div>
</template>

<script setup lang="ts">
import {
  mdiCheck,
  mdiClose,
  mdiLightbulbOnOutline,
  mdiLightbulbOutline,
  mdiMagnify,
  mdiThumbUp,
  mdiThumbUpOutline,
} from "@mdi/js";
import { format, startOfWeek } from "date-fns";
import { useUserApi } from "~/composables/api";
import { useHouseholdPlanner } from "~/composables/use-household-planner";
import type { IdeaOut, StateOut } from "~/lib/api/types/household-planner";
import { toPeople, type PlannerMember } from "~/lib/planner/people";
import { usePlannerPageRefresh } from "~/composables/use-planner-page";
import PlannerSheet from "~/components/Domain/Planner/PlannerSheet.vue";
import PlannerWeekNav from "~/components/Domain/Planner/PlannerWeekNav.vue";

const i18n = useI18n();
const auth = useMealieAuth();
const route = useRoute();
const t = (key: string) => i18n.t(`household-planner.${key}`);
const { api, data, members, busy, error, run, refresh } = useHouseholdPlanner();
const nativeApi = useUserApi();

const initialWeek = typeof route.query.week === "string" ? route.query.week : format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd");
const week = ref(initialWeek);
const number = (v: number | null | undefined) => v == null ? "—" : new Intl.NumberFormat(i18n.locale.value, { maximumFractionDigits: 0 }).format(v);
const imageFor = (recipeId: string) => `/api/media/recipes/${recipeId}/images/min-original.webp`;
const recipeLink = (slug: string) => `/g/${auth.user.value?.groupSlug}/r/${slug}`;
function hideImage(event: Event) { (event.target as HTMLImageElement).style.visibility = "hidden"; }

const people = computed(() => toPeople(members.value as PlannerMember[]));
const person = (id: string) => people.value.find(m => m.id === id);
const memberName = (id: string) => person(id)?.name || "?";

const ideas = computed(() => Object.values(data.value?.state.ideas || {})
  .filter(i => i.week_start === week.value)
  .sort((a, b) => (b.likes?.length || 0) - (a.likes?.length || 0) || a.created_at.localeCompare(b.created_at)));
const plan = computed(() => Object.values(data.value?.state.plans || {}).find(p => p.start === week.value));
const facts = (recipeId: string) => data.value?.state.facts?.[recipeId];
const planned = (recipeId: string) => !!plan.value?.entries?.some(e => e.recipe_id === recipeId);
const liked = (idea: IdeaOut) => !!idea.likes?.includes(auth.user.value?.id || "");

async function write(path: string, payload: unknown, method: "post" | "delete" = "post") {
  if (!data.value) return;
  data.value = await api.write<StateOut>(path, payload, data.value.revision, method);
}
const toggleLike = (id: string) => run(() => write(`/ideas/${id}/like`, {}));
const remove = (id: string) => run(() => write(`/ideas/${id}`, {}, "delete"));

// ---- Proposing ----------------------------------------------------------
const dialog = ref(false);
const search = ref("");
const note = ref("");
const loadingRecipes = ref(false);
const allRecipes = ref<{ id?: string; name?: string }[]>([]);
const filteredRecipes = computed(() => {
  const q = (search.value || "").toLocaleLowerCase();
  return allRecipes.value.filter(r => (r.name || "").toLocaleLowerCase().includes(q)).slice(0, 60);
});

async function openPicker() {
  search.value = "";
  note.value = "";
  dialog.value = true;
  if (allRecipes.value.length) return;
  loadingRecipes.value = true;
  try {
    const response = await nativeApi.recipes.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
    allRecipes.value = response.data?.items || [];
  }
  finally {
    loadingRecipes.value = false;
  }
}

function propose(recipeId: string) {
  run(async () => {
    await write("/ideas", { id: crypto.randomUUID(), week_start: week.value, recipe_id: recipeId, note: note.value || "" });
    dialog.value = false;
  });
}

usePlannerPageRefresh(() => run(refresh), busy);
onMounted(() => run(refresh));
</script>

<style scoped>
.pi {
  --pi-line: var(--fork-hairline);
  --pi-soft: var(--fork-ink-soft);
  max-width: 860px;
}

.pi-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--fork-stack);
}

.pi-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0;
  list-style: none;
}

.pi-card {
  display: grid;
  grid-template-columns: 112px 1fr;
  gap: 14px;
  padding: 10px;
  border: 1px solid var(--pi-line);
  border-radius: var(--fork-radius-card);
  background: rgb(var(--v-theme-surface));
}

.pi-card.is-planned {
  border-color: rgba(var(--v-theme-primary), 0.45);
}

.pi-card__media img {
  width: 112px;
  height: 112px;
  border-radius: 12px;
  object-fit: cover;
  background: rgba(var(--v-theme-primary), 0.08);
}

.pi-card__body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.pi-card__head {
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.pi-card__remove {
  margin: -6px -6px 0 auto;
  color: var(--fork-ink-soft);
}

.pi-card__title {
  overflow-wrap: anywhere;
  font-size: 1.05rem;
  font-weight: 650;
  line-height: 1.3;
  color: inherit;
  text-decoration: none;
}

.pi-card__meta {
  margin-top: 2px;
  font-size: 0.82rem;
  color: var(--pi-soft);
}

.pi-card__note {
  margin-top: 6px;
  font-size: 0.88rem;
}

.pi-card__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 8px;
}

.pi-like {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  color: inherit;
  padding: 0 12px;
  border: 1px solid var(--pi-line);
  border-radius: 999px;
  background: transparent;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}

.pi-like[aria-pressed="true"] {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}

.pi-like:focus-visible,
.pi-pick:focus-visible {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.pi-likers {
  display: inline-flex;
  gap: 3px;
}

.pi-planned {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.85rem;
  font-weight: 650;
  color: rgb(var(--v-theme-primary));
}

.pi-picklist {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
}

.pi-pick {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px;
  border: 1px solid var(--pi-line);
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.pi-pick:hover {
  border-color: rgba(var(--v-theme-primary), 0.55);
}

.pi-pick img {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  object-fit: cover;
  flex: none;
  background: rgba(var(--v-theme-primary), 0.08);
}

.pi-pick span {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.pi-pick small {
  color: var(--pi-soft);
}

@media (max-width: 600px) {
  .pi-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .pi-card {
    grid-template-columns: 76px 1fr;
  }

  .pi-card__media img {
    width: 76px;
    height: 76px;
  }
}
</style>
