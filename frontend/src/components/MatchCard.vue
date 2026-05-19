<template>
  <RouterLink :to="`/match/${match.id}`" class="match-card" :class="{ live: match.status === 'live' }">
    <div class="card-top">
      <span class="group-label">Group {{ TEAM_GROUP[match.home_team] ?? '?' }}</span>
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

    <!-- H2H odds strip -->
    <div v-if="h2hLines.length > 0" class="odds-strip" @click.prevent>
      <OddsButton
        v-for="line in h2hLines"
        :key="line.selection"
        :match-id="match.id"
        market="h2h"
        :selection="line.selection"
        :odds="line.odds"
        :book="line.book"
        :label="selectionLabel(line.selection)"
      />
    </div>
    <div v-else-if="oddsStore.cardH2HLoading" class="odds-strip-skeleton" />

    <div class="card-footer">
      <span class="time">{{ store.formatMatchTime(match.date) }} {{ store.selectedTimezone }}</span>
      <span class="venue" :title="[match.venue, match.city].filter(Boolean).join(', ')">
        {{ [match.venue, match.city].filter(Boolean).join(', ') }}
      </span>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMatchesStore, TEAM_GROUP, type Match } from '../stores/matches'
import { useOddsStore } from '../stores/odds'
import OddsButton from './OddsButton.vue'

const props = defineProps<{ match: Match }>()
const store = useMatchesStore()
const oddsStore = useOddsStore()

const statusLabel = computed(() => {
  if (props.match.status === 'live') return 'LIVE'
  if (props.match.status === 'finished') return 'FT'
  return ''
})

const h2hLines = computed(() => oddsStore.getCardOdds(props.match.id))

function selectionLabel(sel: string): string {
  if (sel === 'draw') return 'Draw'
  const home = props.match.home_team.toLowerCase().replace(/\s+/g, '_')
  const away = props.match.away_team.toLowerCase().replace(/\s+/g, '_')
  if (sel === home) return props.match.home_team
  if (sel === away) return props.match.away_team
  return sel.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
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

.match-card:hover {
  border-color: var(--green);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 200, 83, 0.1);
}

.match-card { transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s; }

.match-card.live {
  border-color: var(--green);
  animation: live-glow 1.8s ease-in-out infinite;
}

@keyframes live-glow {
  0%, 100% { box-shadow: 0 0 8px rgba(0, 200, 83, 0.3); }
  50%       { box-shadow: 0 0 20px rgba(0, 200, 83, 0.7); }
}

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
  min-width: 0;
  overflow: hidden;
}

.team.away { flex-direction: row-reverse; }

.flag { width: 28px; height: 20px; object-fit: cover; border-radius: 2px; flex-shrink: 0; }

.team-name {
  font-weight: 600;
  font-size: 0.95rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score-block { flex-shrink: 0; text-align: center; }
.vs { color: var(--muted); font-size: 0.8rem; }
.score { font-size: 1rem; font-weight: 700; color: var(--text); letter-spacing: 0.03em; }

/* Odds strip */
.odds-strip {
  display: flex;
  gap: 6px;
  margin-bottom: 0.75rem;
}

.odds-strip :deep(.odds-btn) { flex: 1; }

.odds-strip-skeleton {
  height: 52px;
  background: var(--dark);
  border-radius: 6px;
  animation: pulse 1.4s ease-in-out infinite;
  margin-bottom: 0.75rem;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.card-footer {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: var(--muted);
}

.time { white-space: nowrap; flex-shrink: 0; }

.venue {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}
</style>
