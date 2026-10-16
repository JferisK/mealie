<template>
  <PlannerPageShell section="week" :title="$t('household-planner.weekPlan')" :subtitle="$t('household-planner.weekPlanHint')" />
</template>

<script setup lang="ts">
import PlannerPageShell from "~/components/Domain/Planner/PlannerPageShell.vue";
</script>
