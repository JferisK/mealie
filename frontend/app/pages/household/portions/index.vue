<template>
  <PlannerPageShell section="week" :title="$t('household-planner.navWeek')" :subtitle="$t('household-planner.plannedOnly')" />
</template>

<script setup lang="ts">
import PlannerPageShell from "~/components/Domain/Planner/PlannerPageShell.vue";
</script>
