<template>
  <!--
    The one dialog pattern for planner flows: a header that wraps long titles,
    a body that scrolls on its own and a footer that stays reachable above the
    iPhone home indicator. Phones get a full-height sheet (`fullscreen`) or a
    bottom sheet; larger screens a centred card.
  -->
  <v-dialog
    v-model="open"
    scrollable
    :max-width="maxWidth"
    :fullscreen="fullscreen && xs"
    :class="['planner-sheet', { 'planner-sheet--bottom': !fullscreen && xs }]"
  >
    <v-card class="planner-sheet__card" :rounded="xs ? 0 : 'xl'">
      <header class="planner-sheet__header">
        <slot name="prepend" />
        <div class="planner-sheet__titles">
          <h2 class="planner-sheet__title" :title="title">
            {{ title }}
          </h2>
          <p v-if="subtitle" class="planner-sheet__subtitle">
            {{ subtitle }}
          </p>
        </div>
        <v-btn :icon="mdiClose" variant="text" :aria-label="$t('household-planner.close')" @click="open = false" />
      </header>
      <v-card-text class="planner-sheet__body">
        <slot />
      </v-card-text>
      <footer v-if="$slots.actions" class="planner-sheet__actions">
        <slot name="actions" />
      </footer>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { mdiClose } from "@mdi/js";

withDefaults(defineProps<{
  title: string;
  subtitle?: string;
  maxWidth?: number | string;
  fullscreen?: boolean;
}>(), { subtitle: "", maxWidth: 560, fullscreen: false });

const open = defineModel<boolean>({ required: true });
const { xs } = useDisplay();
</script>

<style>
.planner-sheet__card {
  display: flex;
  flex-direction: column;
}

.planner-sheet__header {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 12px 8px 8px 20px;
  border-bottom: 1px solid var(--fork-hairline);
}

.planner-sheet__titles {
  flex: 1;
  min-width: 0;
  padding-top: 10px;
}

.planner-sheet__title {
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.planner-sheet__subtitle {
  margin-top: 2px;
  font-size: 0.88rem;
  color: var(--fork-ink-soft);
}

.planner-sheet__card > .planner-sheet__body.v-card-text {
  padding: 16px 20px;
}

.planner-sheet__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--fork-hairline);
  background: rgb(var(--v-theme-surface));
}

/* Phones: actions share the width; a lone spacer collapses; very long titles
   stop after three lines (full text in the title attribute). */
@media (max-width: 599.98px) {
  .planner-sheet__title {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    overflow: hidden;
  }

  .planner-sheet__header {
    padding-left: 16px;
  }

  .planner-sheet__card > .planner-sheet__body.v-card-text {
    padding: 8px 16px 16px;
  }

  .planner-sheet__actions > .v-btn {
    flex: 1 1 0;
    min-width: 0;
  }

  .planner-sheet__actions > .v-spacer {
    display: none;
  }

  .planner-sheet--bottom > .v-overlay__content {
    align-self: flex-end;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    max-height: calc(100% - 24px - var(--fork-safe-top)) !important;
  }

  .planner-sheet--bottom .planner-sheet__card {
    border-radius: 24px 24px 0 0 !important;
    padding-bottom: var(--fork-safe-bottom);
  }
}
</style>
