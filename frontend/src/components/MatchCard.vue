<template>
  <RouterLink :to="`/match/${match.id}`" class="match-card">
    <div class="card-top">
      <span class="group-label">{{ match.group }}</span>
      <span class="status" :class="match.status">{{ statusLabel }}</span>
    </div>

    <div class="teams">
      <div class="team">
        <img :src="match.home_flag" :alt="match.home_team" class="flag" />
        <span class="team-name">{{ match.home_team }}</span>
      </div>
      <div class="score-block">
        <template v-if="match.home_score != null">
          <span class="score">{{ match.home_score }} – {{ match.away_score }}</span>
        </template>
        <template v-else>
          <span class="vs">vs</span>
        </template>
      </div>
      <div class="team away">
        <span class="team-name">{{ match.away_team }}</span>
        <img :src="match.away_flag" :alt="match.away_team" class="flag" />
      </div>
    </div>

    <div class="card-footer">
      <span class="time">{{ store.formatMatchTime(match.date) }} {{ store.selectedTimezone }}</span>
      <span class="venue">{{ match.venue }}, {{ match.city }}</span>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMatchesStore, type Match } from '../stores/matches'

const props = defineProps<{ match: Match }>()
const store = useMatchesStore()

const statusLabel = computed(() => {
  if (props.match.status === 'live') return 'LIVE'
  if (props.match.status === 'finished') return 'FT'
  return ''
})
</script>

<style scoped>
.match-card {
  display: block;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
  transition: border-color 0.15s;
}

.match-card:hover { border-color: var(--green); }

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-size: 0.75rem;
  color: var(--muted);
}

.status.live { color: #ff4757; font-weight: 700; }
.status.finished { color: var(--muted); }

.teams {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.team {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.team.away { flex-direction: row-reverse; }

.flag { width: 28px; height: 20px; object-fit: cover; border-radius: 2px; }

.team-name { font-weight: 600; font-size: 0.95rem; }

.score-block { flex-shrink: 0; text-align: center; }
.vs { color: var(--muted); font-size: 0.8rem; }
.score { font-size: 1rem; font-weight: 700; color: var(--text); letter-spacing: 0.03em; }

.card-footer {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
  color: var(--muted);
}
</style>
