<template>
  <!-- one recipe's share of one shopping list item; always exactly one line, a long title is cut with "…" -->
  <div
    class="share-row d-flex align-center flex-nowrap text-body-2"
    :class="{ 'share-row--empty': quantity === 0 }"
  >
    <div class="share-row__title" :title="title">
      {{ title }}
    </div>
    <v-btn
      icon
      size="x-small"
      variant="text"
      class="flex-shrink-0"
      :disabled="disabled || draft <= 0"
      :aria-label="$t('shopping-list.share-less')"
      @click="step(-1)"
    >
      <v-icon size="small">
        {{ $globals.icons.minus }}
      </v-icon>
    </v-btn>
    <input
      v-model="text"
      class="share-row__input flex-shrink-0"
      type="number"
      inputmode="decimal"
      min="0"
      step="any"
      :disabled="disabled"
      @focus="($event.target as HTMLInputElement).select()"
      @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
      @blur="commitText"
    >
    <v-btn
      icon
      size="x-small"
      variant="text"
      class="flex-shrink-0"
      :disabled="disabled"
      :aria-label="$t('shopping-list.share-more')"
      @click="step(1)"
    >
      <v-icon size="small">
        {{ $globals.icons.createAlt }}
      </v-icon>
    </v-btn>
    <div class="share-row__unit flex-shrink-0 text-truncate">
      {{ unit }}
    </div>
    <v-btn
      icon
      size="x-small"
      variant="text"
      class="flex-shrink-0"
      :disabled="disabled || quantity === 0"
      :title="$t('shopping-list.remove-recipe-share')"
      :aria-label="$t('shopping-list.remove-recipe-share')"
      @click="commit(0)"
    >
      <v-icon size="small">
        {{ $globals.icons.close }}
      </v-icon>
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core";
import { formatShare } from "~/composables/shopping-list-page/use-recipe-share";

const props = defineProps<{
  title: string;
  quantity: number;
  unit: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{ (e: "update", amount: number): void }>();

// what the row shows while the user is still tapping +/- (saved shortly after the last tap)
const draft = ref(props.quantity);
const text = ref(formatShare(props.quantity));

watch(() => props.quantity, (q) => {
  draft.value = q;
  text.value = formatShare(q);
});

function commit(amount: number) {
  const value = Math.max(0, amount);
  draft.value = value;
  text.value = formatShare(value);
  if (value !== props.quantity) {
    emit("update", value);
  }
}

const commitDebounced = useDebounceFn(() => commit(draft.value), 600);

function step(delta: number) {
  draft.value = Math.max(0, Math.round((draft.value + delta) * 100) / 100);
  text.value = formatShare(draft.value);
  commitDebounced();
}

function commitText() {
  const parsed = parseFloat(String(text.value).replace(",", "."));
  if (!Number.isFinite(parsed)) {
    // empty or garbage: back to what it was
    text.value = formatShare(draft.value);
    return;
  }
  commit(parsed);
}
</script>

<style scoped>
.share-row {
  min-height: 32px;
  gap: 2px;
}

.share-row__title {
  flex: 1 1 auto;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.share-row__input {
  width: 3.5rem;
  text-align: center;
  padding: 2px 4px;
  border-radius: 6px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  color: inherit;
  font: inherit;
  -moz-appearance: textfield;
  appearance: textfield;
}

.share-row__input::-webkit-outer-spin-button,
.share-row__input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.share-row__unit {
  max-width: 4rem;
  margin-left: 2px;
}

.share-row--empty .share-row__title,
.share-row--empty .share-row__unit {
  text-decoration: line-through;
  opacity: 0.5;
}
</style>
