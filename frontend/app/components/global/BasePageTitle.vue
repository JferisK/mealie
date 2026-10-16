<template>
  <!-- Fork: same header pattern as the planner pages (fork-page__*), with the
       illustration kept small so content starts higher on phones. -->
  <div class="base-page-title">
    <section class="base-page-title__main">
      <div class="base-page-title__text">
        <h1 class="fork-page__title">
          <slot name="title">
            👋 Here's a Title
          </slot>
        </h1>
        <p v-if="$slots.default" class="fork-page__subtitle">
          <slot />
        </p>
      </div>
      <div v-if="$slots.header" class="base-page-title__art">
        <slot name="header" />
      </div>
    </section>
    <section class="d-flex">
      <slot name="content" />
    </section>
    <v-divider
      v-if="divider"
      class="mt-4 mb-4"
    />
  </div>
</template>

<script setup lang="ts">
defineProps({
  divider: {
    type: Boolean,
    default: false,
  },
});
</script>

<style scoped>
.base-page-title {
  margin-top: 8px;
}

.base-page-title__main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}

.base-page-title__text {
  flex: 1;
  min-width: 0;
}

/* Non-image header content (e.g. a toolbar) stays a full-width row above. */
.base-page-title__art {
  order: -1;
  flex: 1 0 100%;
  min-width: 0;
}

.base-page-title__art:has(> .v-img, > .v-responsive) {
  order: 0;
  flex: none;
  width: 72px;
  opacity: 0.9;
}

.base-page-title__art :deep(.v-img),
.base-page-title__art :deep(.v-responsive) {
  max-width: 72px !important;
  max-height: 72px !important;
}

@media (min-width: 960px) {
  .base-page-title__art:has(> .v-img, > .v-responsive) {
    width: 96px;
  }

  .base-page-title__art :deep(.v-img),
  .base-page-title__art :deep(.v-responsive) {
    max-width: 96px !important;
    max-height: 96px !important;
  }
}
</style>
