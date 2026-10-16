<template>
  <div class="planner-page">
    <header class="planner-page__header">
      <h1 class="planner-page__title">
        {{ title }}
      </h1>
      <p v-if="subtitle" class="planner-page__subtitle">
        {{ subtitle }}
      </p>
    </header>
    <PlannerPortions :section="section" />
  </div>
</template>

<script setup lang="ts">
import PlannerPortions from "~/components/Domain/Planner/PlannerPortions.vue";

const props = defineProps<{
  section: "week" | "cook" | "freezer" | "goals";
  title: string;
  subtitle?: string;
}>();

useSeoMeta({ title: () => props.title });
</script>

<style scoped>
.planner-page {
  max-width: 1180px;
  margin: 0 auto;
}

.planner-page__header {
  padding: 28px 16px 4px;
}

.planner-page__title {
  font-size: clamp(1.75rem, 1.4rem + 1.2vw, 2.4rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.planner-page__subtitle {
  margin-top: 6px;
  max-width: 62ch;
  color: rgba(var(--v-theme-on-background), 0.66);
}
</style>
