<template>
  <div class="group-filter">
    <button
      v-for="g in groups"
      :key="g.value"
      class="group-btn"
      :class="{ active: store.selectedGroup === g.value }"
      @click="store.selectedGroup = g.value"
    >
      {{ g.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useMatchesStore } from '../stores/matches'

const store = useMatchesStore()

const groups = [
  { value: 'all', label: 'All' },
  { value: 'Group Stage - 1', label: 'Matchday 1' },
  { value: 'Group Stage - 2', label: 'Matchday 2' },
  { value: 'Group Stage - 3', label: 'Matchday 3' },
]
</script>

<style scoped>
.group-filter {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.group-btn {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid var(--border);
  font-size: 0.85rem;
  color: var(--muted);
  transition: border-color 0.15s, color 0.15s;
}

.group-btn:hover { color: var(--text); border-color: var(--text); }

.group-btn.active {
  border-color: var(--green);
  color: var(--green);
  font-weight: 600;
}
</style>
