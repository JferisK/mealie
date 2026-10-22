<template>
  <!-- quick entry at the end of a category: type "Gurke" or "2 Gurken", Enter adds it and keeps the field open -->
  <div class="quick-add">
    <v-text-field
      v-if="open"
      ref="input"
      v-model="text"
      :placeholder="$t('shopping-list.quick-add-placeholder')"
      :prepend-inner-icon="$globals.icons.createAlt"
      density="compact"
      variant="solo-filled"
      flat
      hide-details
      autofocus
      enterkeyhint="done"
      @keydown.enter.prevent="submit"
      @keydown.esc="close"
      @blur="text.trim() ? undefined : close()"
    >
      <template #append-inner>
        <v-btn
          :icon="$globals.icons.check"
          :aria-label="$t('general.add')"
          size="small"
          variant="text"
          :disabled="!text.trim()"
          @mousedown.prevent
          @click="submit"
        />
      </template>
    </v-text-field>
    <v-btn
      v-else
      :prepend-icon="$globals.icons.createAlt"
      variant="text"
      size="small"
      class="text-medium-emphasis"
      @click="open = true"
    >
      {{ $t('shopping-list.quick-add') }}
    </v-btn>
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits<{ (e: "add", text: string): void }>();

const open = ref(false);
const text = ref("");

function submit() {
  if (!text.value.trim()) {
    return;
  }
  emit("add", text.value);
  text.value = "";
}

function close() {
  open.value = false;
  text.value = "";
}
</script>

<style scoped>
.quick-add {
  padding: 4px 8px 6px;
}
</style>
