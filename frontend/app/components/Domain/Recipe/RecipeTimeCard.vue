<template v-if="_showCards">
  <!-- Fork: compact one-line variant for the recipe header -->
  <ul v-if="inline" class="time-inline">
    <li v-for="item in inlineItems" :key="item.name">
      <v-icon size="18" color="primary">
        {{ item.icon }}
      </v-icon>
      <span><strong>{{ item.value }}</strong> {{ item.name }}</span>
    </li>
  </ul>
  <div v-else class="text-center">
    <!-- Total Time -->
    <div
      v-if="validateTotalTime"
      class="time-card-flex mx-auto"
    >
      <v-row
        no-gutters
        class="d-flex flex-no-wrap align-center"
        :style="fontSize"
      >
        <v-icon
          :x-large="!small"
          start
          color="primary"
        >
          {{ $globals.icons.clockOutline }}
        </v-icon>
        <p class="my-0">
          <span class="font-weight-bold opacity-80">{{ validateTotalTime.name }}</span><br>{{ validateTotalTime.value }}
        </p>
      </v-row>
    </div>
    <v-divider
      v-if="validateTotalTime && (validatePrepTime || validatePerformTime)"
      class="my-2"
    />
    <!-- Prep Time & Perform Time -->
    <div
      v-if="validatePrepTime || validatePerformTime"
      class="time-card-flex mx-auto"
    >
      <v-row
        no-gutters
        class="d-flex justify-center align-center"
        :class="{ 'flex-column': $vuetify.display.smAndDown }"
        style="width: 100%;"
        :style="fontSize"
      >
        <div
          v-if="validatePrepTime"
          class="d-flex flex-no-wrap my-1 align-center"
        >
          <v-icon
            :size="small ? 'small' : 'large'"
            start
            color="primary"
          >
            {{ $globals.icons.knife }}
          </v-icon>
          <p class="my-0">
            <span class="font-weight-bold opacity-80">{{ validatePrepTime.name }}</span><br>{{ validatePrepTime.value }}
          </p>
        </div>
        <v-divider
          v-if="validatePrepTime && validatePerformTime"
          vertical
          class="mx-4"
        />
        <div
          v-if="validatePerformTime"
          class="d-flex flex-no-wrap my-1 align-center"
        >
          <v-icon
            :size="small ? 'small' : 'large'"
            start
            color="primary"
          >
            {{ $globals.icons.potSteam }}
          </v-icon>
          <p class="my-0">
            <span class="font-weight-bold opacity-80">{{ validatePerformTime.name }}</span><br>{{ validatePerformTime.value }}
          </p>
        </div>
      </v-row>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  prepTime?: string | null;
  totalTime?: string | null;
  performTime?: string | null;
  color?: string;
  small?: boolean;
  inline?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  prepTime: null,
  totalTime: null,
  performTime: null,
  color: "accent custom-transparent",
  small: false,
  inline: false,
});
const { $globals } = useNuxtApp();

const i18n = useI18n();

function isEmpty(str: string | null) {
  return !str || str.length === 0;
}

const _showCards = computed(() => {
  return [props.prepTime, props.totalTime, props.performTime].some(x => !isEmpty(x));
});

const validateTotalTime = computed(() => {
  return !isEmpty(props.totalTime) ? { name: i18n.t("recipe.total-time"), value: props.totalTime } : null;
});

const validatePrepTime = computed(() => {
  return !isEmpty(props.prepTime) ? { name: i18n.t("recipe.prep-time"), value: props.prepTime } : null;
});

const validatePerformTime = computed(() => {
  return !isEmpty(props.performTime) ? { name: i18n.t("recipe.perform-time"), value: props.performTime } : null;
});

const inlineItems = computed(() => [
  validateTotalTime.value && { ...validateTotalTime.value, icon: $globals.icons.clockOutline },
  validatePrepTime.value && { ...validatePrepTime.value, icon: $globals.icons.knife },
  validatePerformTime.value && { ...validatePerformTime.value, icon: $globals.icons.potSteam },
].filter(Boolean) as { name: string; value: string; icon: string }[]);

const fontSize = computed(() => {
  return props.small ? { fontSize: "smaller" } : { fontSize: "larger" };
});
</script>

<style scoped>
.text-center {
  font-size: smaller;
}
.time-card-flex {
  width: fit-content;
}
.time-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.9rem;
}
.time-inline li {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.time-inline span {
  color: var(--fork-ink-soft);
}
.time-inline strong {
  color: rgb(var(--v-theme-on-surface));
  font-weight: 650;
}
.custom-transparent {
  opacity: 0.7;
}
</style>
