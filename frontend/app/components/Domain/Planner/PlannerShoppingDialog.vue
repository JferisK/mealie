<template>
  <BaseDialog
    v-model="dialog"
    bottom-sheet
    :title="$t('recipe.add-to-list')"
    :icon="$globals.icons.cartCheck"
  >
    <v-progress-linear v-if="loading" indeterminate />
    <v-alert v-if="failure" type="error" variant="tonal" density="compact" class="ma-4">
      {{ failure }}
    </v-alert>
    <!-- No dead end – create the first list right here -->
    <div v-if="lists && !lists.length" class="pa-4">
      <p class="text-medium-emphasis mb-3">
        {{ $t('shopping-list.no-shopping-lists-found') }}
      </p>
      <div class="d-flex ga-2 align-center">
        <v-text-field
          v-model.trim="newListName"
          :label="$t('shopping-list.new-list')"
          variant="outlined"
          density="comfortable"
          hide-details
          @keydown.enter.stop.prevent="createList"
        />
        <v-btn color="primary" variant="flat" :loading="loading" :disabled="!newListName" @click="createList">
          {{ $t('general.create') }}
        </v-btn>
      </div>
    </div>
    <v-card-text v-else>
      <v-card
        v-for="list in lists"
        :key="list.id"
        hover
        :disabled="loading"
        class="my-2 left-border"
        @click="add(list.id)"
      >
        <v-card-title class="py-2">
          {{ list.name }}
        </v-card-title>
      </v-card>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { useHouseholdPlanner } from "~/composables/use-household-planner";
import type { ShoppingListSummary } from "~/lib/api/types/household";
import type { StateOut } from "~/lib/api/types/household-planner";

// Links the week to a native list: dishes appear with portions and the list follows later plan changes.
const props = defineProps<{ planId: string; revision: number }>();
const emit = defineEmits<{ added: [state: StateOut] }>();
const dialog = defineModel<boolean>({ default: false });

const i18n = useI18n();
const nativeApi = useUserApi();
const { api } = useHouseholdPlanner();
const lists = ref<ShoppingListSummary[] | null>(null);
const loading = ref(false);
const failure = ref("");
const newListName = ref(i18n.t("shopping-list.shopping-list"));

async function guarded(action: () => Promise<void>) {
  loading.value = true;
  failure.value = "";
  try { await action(); }
  catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    failure.value = typeof detail === "string" ? detail : i18n.t("recipe.failed-to-add-recipes-to-list");
  }
  finally { loading.value = false; }
}

watch(dialog, (open) => {
  if (!open) return;
  lists.value = null;
  guarded(async () => {
    const { data } = await nativeApi.shopping.lists.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
    lists.value = (data?.items as ShoppingListSummary[]) ?? [];
  });
});

async function addTo(listId: string) {
  const state = await api.addToShoppingList(props.planId, listId, props.revision);
  dialog.value = false;
  emit("added", state);
}

function add(listId: string) {
  guarded(() => addTo(listId));
}

function createList() {
  if (!newListName.value) return;
  guarded(async () => {
    const { data } = await nativeApi.shopping.lists.createOne({ name: newListName.value });
    if (!data?.id) throw new Error("Empty response");
    lists.value = [data as unknown as ShoppingListSummary];
    await addTo(data.id);
  });
}
</script>
