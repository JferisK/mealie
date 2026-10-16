<template>
  <nav class="planner-weeknav" :aria-label="$t('household-planner.weekPlan')">
    <v-btn
      :icon="mdiChevronLeft"
      variant="text"
      :aria-label="$t('household-planner.previous')"
      :disabled="disabled"
      @click="shift(-7)"
    />
    <button type="button" class="planner-weeknav__label" :disabled="disabled || isCurrent" :title="$t('household-planner.thisWeek')" @click="week = currentWeek">
      <strong>{{ $t('household-planner.weekShort') }} {{ weekNumber }}<span v-if="isCurrent" class="planner-weeknav__now">{{ $t('household-planner.thisWeek') }}</span></strong>
      <span>{{ shortDate(week) }} – {{ shortDate(weekEnd) }}</span>
    </button>
    <v-btn
      :icon="mdiChevronRight"
      variant="text"
      :aria-label="$t('household-planner.next')"
      :disabled="disabled"
      @click="shift(7)"
    />
  </nav>
</template>

<script setup lang="ts">
import { mdiChevronLeft, mdiChevronRight } from "@mdi/js";
import { addDays, format, getISOWeek, parseISO, startOfWeek } from "date-fns";

defineProps<{ disabled?: boolean }>();
// Monday of the shown week as yyyy-MM-dd.
const week = defineModel<string>({ required: true });

const i18n = useI18n();
const currentWeek = format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd");
const isCurrent = computed(() => week.value === currentWeek);
const weekEnd = computed(() => format(addDays(parseISO(week.value), 6), "yyyy-MM-dd"));
const weekNumber = computed(() => getISOWeek(parseISO(week.value)));
const shortDate = (d: string) => new Intl.DateTimeFormat(i18n.locale.value, { day: "numeric", month: "short" }).format(parseISO(d));

function shift(days: number) {
  week.value = format(addDays(parseISO(week.value), days), "yyyy-MM-dd");
}
</script>

<style scoped>
.planner-weeknav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  min-width: 0;
}

.planner-weeknav__label {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 148px;
  min-height: 44px;
  justify-content: center;
  padding: 2px 8px;
  border: 0;
  border-radius: var(--fork-radius-control);
  background: transparent;
  color: inherit;
  font: inherit;
  line-height: 1.25;
  cursor: pointer;
}

.planner-weeknav__label:disabled {
  cursor: default;
}

.planner-weeknav__label:not(:disabled):hover {
  background: var(--fork-tint);
}

.planner-weeknav__label > span {
  font-size: 0.82rem;
  color: var(--fork-ink-soft);
}

.planner-weeknav__now {
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--fork-tint);
  color: rgb(var(--v-theme-primary));
  font-size: 0.7rem;
  font-weight: 700;
  vertical-align: 2px;
}
</style>
