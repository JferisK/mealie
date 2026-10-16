<template>
  <div />
</template>

<script setup lang="ts">
const routes: Record<string, string> = { cook: "/household/cooking", freezer: "/household/freezer", goals: "/household/goals" };
const { section, ...query } = useRoute().query;
await navigateTo({ path: routes[String(section)] || "/household/portions", query }, { replace: true });
</script>
