<template>
  <button
    class="odds-btn"
    :class="{ active: isActive }"
    @click="toggle"
    :title="label"
  >
    <span class="odds-label">{{ shortLabel }}</span>
    <span class="odds-value">{{ odds }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useParlayStore, type Pick } from '../stores/parlay'

const props = defineProps<{
  matchId: number
  market: string
  selection: string
  odds: string
  book: string
  label: string
}>()

const parlay = useParlayStore()

const pickId = computed(() => `${props.matchId}:${props.market}:${props.selection}:${props.book}`)
const isActive = computed(() => parlay.hasPick(pickId.value))

const shortLabel = computed(() => {
  const map: Record<string, string> = {
    draw: 'Draw', over: 'Over', under: 'Under',
    yes: 'Yes', no: 'No', both_teams_to_score: 'BTTS',
  }
  return map[props.selection]
    ?? props.selection.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
})

function toggle() {
  if (isActive.value) {
    parlay.removePick(pickId.value)
  } else {
    const pick: Pick = {
      id: pickId.value,
      match_id: props.matchId,
      label: props.label,
      odds: props.odds,
      market: props.market,
      book: props.book,
    }
    parlay.addPick(pick)
  }
}
</script>

<style scoped>
.odds-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  transition: border-color 0.15s, background 0.15s;
  gap: 2px;
  min-width: 0;
}

.odds-btn:hover { border-color: var(--green); }

.odds-btn.active {
  border-color: var(--green);
  background: color-mix(in srgb, var(--green) 15%, var(--surface));
}

.odds-label { font-size: 0.72rem; color: var(--muted); }
.odds-btn.active .odds-label { color: var(--green); }

.odds-value { font-size: 0.9rem; font-weight: 700; }
</style>
