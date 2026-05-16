<template>
  <div class="tz-toggle">
    <button
      v-for="tz in timezones"
      :key="tz"
      class="tz-btn"
      :class="{ active: store.selectedTimezone === tz }"
      @click="store.selectedTimezone = tz"
    >
      {{ tz }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useMatchesStore, type Timezone } from '../stores/matches'

const store = useMatchesStore()
const timezones: Timezone[] = ['ET', 'CT', 'MT', 'PT']
</script>

<style scoped>
.tz-toggle {
  display: flex;
  gap: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 3px;
}

.tz-btn {
  padding: 4px 10px;
  border-radius: 5px;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--muted);
  transition: background 0.15s, color 0.15s;
}

.tz-btn.active {
  background: var(--green);
  color: #000;
}
</style>
