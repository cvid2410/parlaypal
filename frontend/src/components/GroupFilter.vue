<template>
  <div class="team-filter">
    <div class="search-row">
      <div class="chips-input" :class="{ focused }" @click="focusInput">
        <span
          v-for="team in store.selectedTeams"
          :key="team"
          class="chip"
        >
          <img :src="flagFor(team)" :alt="team" class="chip-flag" />
          {{ team }}
          <button class="chip-remove" @click.stop="remove(team)">✕</button>
        </span>
        <input
          ref="inputEl"
          v-model="query"
          class="inner-input"
          placeholder="Filter by team…"
          @focus="focused = true; open = true"
          @blur="onBlur"
          @keydown.escape="open = false"
          @keydown.backspace="onBackspace"
        />
      </div>
      <button v-if="store.selectedTeams.length" class="clear-all-btn" @click="clearAll">Clear all</button>
    </div>

    <div v-if="open && suggestions.length" class="dropdown">
      <button
        v-for="team in suggestions"
        :key="team.name"
        class="team-option"
        :class="{ active: store.selectedTeams.includes(team.name) }"
        @mousedown.prevent="toggle(team.name)"
      >
        <img :src="team.flag" :alt="team.name" class="flag" />
        {{ team.name }}
        <span v-if="store.selectedTeams.includes(team.name)" class="check">✓</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMatchesStore } from '../stores/matches'

const store = useMatchesStore()
const query = ref('')
const open = ref(false)
const focused = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

const suggestions = computed(() => {
  const q = query.value.toLowerCase()
  return store.allTeams
    .filter(name => name.toLowerCase().includes(q))
    .map(name => {
      const match = store.matches.find(m => m.home_team === name || m.away_team === name)
      const flag = match?.home_team === name ? match.home_flag : match?.away_flag ?? ''
      return { name, flag }
    })
})

function flagFor(name: string): string {
  const match = store.matches.find(m => m.home_team === name || m.away_team === name)
  return match?.home_team === name ? match.home_flag : match?.away_flag ?? ''
}

function toggle(name: string) {
  const idx = store.selectedTeams.indexOf(name)
  if (idx === -1) {
    store.selectedTeams.push(name)
  } else {
    store.selectedTeams.splice(idx, 1)
  }
  query.value = ''
  inputEl.value?.focus()
}

function remove(name: string) {
  const idx = store.selectedTeams.indexOf(name)
  if (idx !== -1) store.selectedTeams.splice(idx, 1)
}

function clearAll() {
  store.selectedTeams.splice(0)
  query.value = ''
}

function focusInput() {
  inputEl.value?.focus()
}

function onBackspace() {
  if (!query.value && store.selectedTeams.length) {
    store.selectedTeams.splice(store.selectedTeams.length - 1, 1)
  }
}

function onBlur() {
  setTimeout(() => {
    focused.value = false
    open.value = false
  }, 150)
}
</script>

<style scoped>
.team-filter { position: relative; }

.search-row { display: flex; align-items: center; gap: 0.5rem; }

.chips-input {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  min-height: 36px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px 12px;
  cursor: text;
  flex: 1;
  max-width: 480px;
  transition: border-color 0.15s;
}

.chips-input.focused { border-color: var(--green); }

.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--dark);
  border: 1px solid var(--green);
  color: var(--green);
  font-size: 0.78rem;
  font-weight: 600;
  border-radius: 12px;
  padding: 2px 6px 2px 4px;
  white-space: nowrap;
}

.chip-flag { width: 16px; height: 11px; object-fit: cover; border-radius: 2px; }

.chip-remove {
  font-size: 0.65rem;
  color: var(--green);
  padding: 0;
  line-height: 1;
  opacity: 0.7;
}
.chip-remove:hover { opacity: 1; }

.inner-input {
  border: none;
  background: transparent;
  outline: none;
  font-size: 0.85rem;
  color: var(--text);
  min-width: 100px;
  flex: 1;
}
.inner-input::placeholder { color: var(--muted); }

.clear-all-btn {
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.78rem;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
}
.clear-all-btn:hover { color: var(--text); border-color: var(--text); }

.dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 50;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  width: 260px;
  max-height: 300px;
  overflow-y: auto;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

.team-option {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  font-size: 0.85rem;
  color: var(--text);
  text-align: left;
  transition: background 0.1s;
}

.team-option:hover { background: var(--dark); }
.team-option.active { color: var(--green); font-weight: 600; }

.flag { width: 22px; height: 15px; object-fit: cover; border-radius: 2px; flex-shrink: 0; }

.check { margin-left: auto; font-size: 0.75rem; color: var(--green); }
</style>
