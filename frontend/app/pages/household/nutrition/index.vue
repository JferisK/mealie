<template>
  <div class="nutrition-page">
    <header class="nutrition-header">
      <h1 class="nutrition-title">
        {{ $t("household-planner.nutritionNav") }}
      </h1>
      <p class="nutrition-subtitle">
        {{ $t("household-planner.subtitle") }}
      </p>
      <v-tabs v-model="section" color="primary" density="comfortable" class="nutrition-tabs">
        <v-tab v-for="item in sections" :key="item.value" :value="item.value" :prepend-icon="item.icon">
          {{ item.title }}
        </v-tab>
      </v-tabs>
    </header>
    <PlannerPortions />
  </div>
</template>

<script setup lang="ts">
import { mdiCalendarWeek, mdiPotSteam, mdiSnowflake, mdiTarget } from "@mdi/js";
import PlannerPortions from "~/components/Domain/Planner/PlannerPortions.vue";

const i18n = useI18n();
const route = useRoute();
const router = useRouter();

useSeoMeta({ title: i18n.t("household-planner.nutritionNav") });

const sections = computed(() => [
  { value: "week", title: i18n.t("household-planner.navWeek"), icon: mdiCalendarWeek },
  { value: "cook", title: i18n.t("household-planner.cookTab"), icon: mdiPotSteam },
  { value: "freezer", title: i18n.t("household-planner.stockTab"), icon: mdiSnowflake },
  { value: "goals", title: i18n.t("household-planner.goalsTab"), icon: mdiTarget },
]);

const section = computed({
  get: () => ["freezer", "cook", "goals"].includes(String(route.query.section)) ? String(route.query.section) : "week",
  set: (value: string) => {
    const { section: _old, ...rest } = route.query;
    router.replace({ query: value === "week" ? rest : { ...rest, section: value } });
  },
});
</script>

<style scoped>
.nutrition-page {
  max-width: 1180px;
  margin: 0 auto;
}

.nutrition-header {
  padding: 28px 16px 0;
}

.nutrition-title {
  font-size: clamp(1.75rem, 1.4rem + 1.2vw, 2.4rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.nutrition-subtitle {
  margin-top: 6px;
  color: rgba(var(--v-theme-on-background), 0.66);
}

.nutrition-tabs {
  margin-top: 18px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
