<template>
  <div class="team-filter">
    <div class="search-row">
      <input
        v-model="query"
        class="search-input"
        placeholder="Filter by team…"
        @focus="open = true"
        @blur="onBlur"
      />
      <button v-if="store.selectedTeam" class="clear-btn" @click="clear">✕ {{ store.selectedTeam }}</button>
    </div>

    <div v-if="open && filtered.length" class="dropdown">
      <button
        v-for="team in filtered"
        :key="team.name"
        class="team-option"
        :class="{ active: store.selectedTeam === team.name }"
        @mousedown.prevent="select(team.name)"
      >
        <img :src="team.flag" :alt="team.name" class="flag" />
        {{ team.name }}
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

const filtered = computed(() => {
  const q = query.value.toLowerCase()
  return store.allTeams
    .filter(name => name.toLowerCase().includes(q))
    .map(name => {
      const match = store.matches.find(m => m.home_team === name || m.away_team === name)
      const flag = match?.home_team === name ? match.home_flag : match?.away_flag ?? ''
      return { name, flag }
    })
})

function select(team: string) {
  store.selectedTeam = team
  query.value = ''
  open.value = false
}

function clear() {
  store.selectedTeam = ''
  query.value = ''
}

function onBlur() {
  setTimeout(() => { open.value = false }, 150)
}
</script>

<style scoped>
.team-filter { position: relative; }

.search-row { display: flex; align-items: center; gap: 0.5rem; }

.search-input {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 0.85rem;
  color: var(--text);
  width: 200px;
  outline: none;
  transition: border-color 0.15s;
}

.search-input:focus { border-color: var(--green); }
.search-input::placeholder { color: var(--muted); }

.clear-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid var(--green);
  color: var(--green);
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
}

.dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 50;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  width: 240px;
  max-height: 280px;
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
</style>
