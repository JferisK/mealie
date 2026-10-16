<template>
  <div class="fork-page">
    <header class="fork-page__header">
      <div class="fork-page__heading">
        <h1 class="fork-page__title">
          {{ title }}
        </h1>
        <p v-if="subtitle" class="fork-page__subtitle">
          {{ subtitle }}
        </p>
      </div>
      <div class="planner-page__actions">
        <v-btn
          v-if="section === 'week'"
          variant="text"
          :prepend-icon="mdiCalendarMonth"
          to="/household/mealplan/planner/view"
        >
          {{ $t("household-planner.calendarView") }}
        </v-btn>
        <v-btn
          v-if="page.refresh.value"
          :icon="mdiRefresh"
          variant="text"
          :loading="page.busy.value"
          :aria-label="$t('household-planner.refresh')"
          @click="page.refresh.value?.()"
        />
      </div>
    </header>
    <PlannerWeek v-if="section === 'week'" />
    <PlannerIdeas v-else-if="section === 'ideas'" />
    <PlannerPortions v-else :section="section" />
  </div>
</template>

<script setup lang="ts">
import { mdiCalendarMonth, mdiRefresh } from "@mdi/js";
import PlannerPortions from "~/components/Domain/Planner/PlannerPortions.vue";
import PlannerWeek from "~/components/Domain/Planner/PlannerWeek.vue";
import PlannerIdeas from "~/components/Domain/Planner/PlannerIdeas.vue";
import { useAuthBackend } from "~/composables/use-auth-backend";
import { providePlannerPage } from "~/composables/use-planner-page";

const props = defineProps<{
  section: "ideas" | "week" | "cook" | "freezer" | "goals";
  title: string;
  subtitle?: string;
}>();

useSeoMeta({ title: () => props.title });
const page = providePlannerPage();

// Household planner data is private; send signed-out visitors to the login and back.
const authBackend = useAuthBackend();
const route = useRoute();
watch(() => authBackend.status.value, (status) => {
  if (status === "unauthenticated") {
    navigateTo(`/login?redirect=${encodeURIComponent(route.fullPath)}`);
  }
}, { immediate: true });
</script>

<style scoped>
.planner-page__actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: -8px;
}

@media (max-width: 599.98px) {
  /* Icon only on phones; the label stays for screen readers. */
  .planner-page__actions :deep(.v-btn:not(.v-btn--icon) .v-btn__content) {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }

  .planner-page__actions :deep(.v-btn:not(.v-btn--icon) .v-btn__prepend) {
    margin: 0;
  }
}
</style>
