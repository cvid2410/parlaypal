<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">WC 2026 Bracket</h1>
      <p class="subtitle">{{ rounds.length ? `Knockout stage — ${totalMatches} matches` : 'Begins June 27, 2026' }}</p>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="bracket-scroll">
      <div v-for="r in 6" :key="r" class="round-col">
        <div class="round-label skeleton-label" />
        <div v-for="i in Math.ceil(16 / r)" :key="i" class="skeleton-match" />
      </div>
    </div>

    <!-- TBD Ghost Bracket -->
    <div v-else-if="rounds.length === 0" class="bracket-scroll">
      <div
        v-for="(round, ri) in PLACEHOLDER_ROUNDS"
        :key="round.name"
        class="round-col"
        :style="`--ri: ${ri}`"
      >
        <h2 class="round-label animate-label" :class="{ 'final-label': ri === PLACEHOLDER_ROUNDS.length - 1 }">
          {{ round.name }}
        </h2>
        <div class="match-stack">
          <div
            v-for="ci in round.count"
            :key="ci"
            class="bracket-card tbd shimmer-card"
            :style="`--delay: ${(ri * 0.12 + ci * 0.04).toFixed(2)}s`"
          >
            <div class="bracket-time tbd-text">Jun 27+</div>
            <div class="bracket-team">
              <div class="tbd-flag" />
              <span class="b-name tbd-text">TBD</span>
            </div>
            <div class="bracket-team">
              <div class="tbd-flag" />
              <span class="b-name tbd-text">TBD</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Live Bracket -->
    <div v-else class="bracket-scroll">
      <div
        v-for="(round, ri) in rounds"
        :key="round.name"
        class="round-col"
        :style="`--ri: ${ri}`"
      >
        <h2 class="round-label animate-label" :class="{ 'final-label': round.name === 'Final' }">
          {{ round.name }}
        </h2>
        <div class="match-stack">
          <div
            v-for="(match, ci) in round.matches"
            :key="match.id"
            class="bracket-card animate-card"
            :class="{ live: match.status === 'live', final: round.name === 'Final' }"
            :style="`--delay: ${(ri * 0.12 + ci * 0.05).toFixed(2)}s`"
            @click="router.push(`/match/${match.id}`)"
          >
            <div class="bracket-time">{{ store.formatMatchTime(match.date) }} {{ store.selectedTimezone }}</div>
            <div class="bracket-team" :class="{ winner: isWinner(match, 'home') }">
              <img :src="match.home_flag" :alt="match.home_team" class="b-flag" />
              <span class="b-name">{{ match.home_team }}</span>
              <span v-if="match.home_score != null" class="b-score">{{ match.home_score }}</span>
            </div>
            <div class="bracket-team" :class="{ winner: isWinner(match, 'away') }">
              <img :src="match.away_flag" :alt="match.away_team" class="b-flag" />
              <span class="b-name">{{ match.away_team }}</span>
              <span v-if="match.away_score != null" class="b-score">{{ match.away_score }}</span>
            </div>
            <div v-if="match.status === 'live'" class="live-badge">LIVE</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMatchesStore, type Match } from '../stores/matches'

const store = useMatchesStore()
const router = useRouter()

const PLACEHOLDER_ROUNDS = [
  { name: 'Round of 32',     count: 16 },
  { name: 'Round of 16',     count: 8 },
  { name: 'Quarter-finals',  count: 4 },
  { name: 'Semi-finals',     count: 2 },
  { name: '3rd Place Final', count: 1 },
  { name: 'Final',           count: 1 },
]

const ROUND_ORDER = PLACEHOLDER_ROUNDS.map(r => r.name)

const rounds = computed(() => {
  const map = new Map<string, Match[]>()
  for (const match of store.matches) {
    const round = ROUND_ORDER.find(r => match.group.toLowerCase().includes(r.toLowerCase()))
    if (!round) continue
    if (!map.has(round)) map.set(round, [])
    map.get(round)!.push(match)
  }
  return ROUND_ORDER
    .filter(r => map.has(r))
    .map(r => ({ name: r, matches: map.get(r)!.sort((a, b) => a.date.localeCompare(b.date)) }))
})

const totalMatches = computed(() => rounds.value.reduce((n, r) => n + r.matches.length, 0))

function isWinner(match: Match, side: 'home' | 'away'): boolean {
  if (match.status !== 'finished' || match.home_score == null || match.away_score == null) return false
  return side === 'home' ? match.home_score > match.away_score : match.away_score > match.home_score
}

onMounted(async () => {
  if (store.matches.length === 0) await store.loadMatches()
})
</script>

<style scoped>
.page-header { margin-bottom: 1.5rem; }
.page-title { font-size: 1.5rem; font-weight: 700; }
.subtitle { color: var(--muted); font-size: 0.85rem; margin-top: 2px; }

/* ── Layout ── */
.bracket-scroll {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  padding-bottom: 1.5rem;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.round-col {
  flex-shrink: 0;
  width: 200px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.match-stack { display: flex; flex-direction: column; gap: 0.5rem; }

/* ── Round label ── */
.round-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  padding: 4px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.25rem;
  white-space: nowrap;
}

.final-label {
  color: var(--green);
  border-bottom-color: var(--green);
  text-shadow: 0 0 12px color-mix(in srgb, var(--green) 60%, transparent);
}

.animate-label {
  animation: label-drop calc(0.35s + var(--ri, 0) * 0.08s) cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(var(--ri, 0) * 0.1s);
}

@keyframes label-drop {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Loading skeleton ── */
.skeleton-label {
  height: 18px;
  background: var(--surface);
  border-radius: 4px;
  animation: pulse 1.4s ease-in-out infinite;
}

.skeleton-match {
  height: 80px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ── Bracket card base ── */
.bracket-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.5rem 0.625rem;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
}

.bracket-card:hover {
  border-color: var(--green);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 200, 83, 0.12);
}

/* ── Slide-in animation ── */
.animate-card {
  animation: slide-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--delay, 0s);
}

@keyframes slide-in {
  from { opacity: 0; transform: translateX(-18px); }
  to   { opacity: 1; transform: translateX(0); }
}

/* ── Live card ── */
.bracket-card.live {
  border-color: #ff4757;
  animation: slide-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) both,
             live-glow 1.8s ease-in-out infinite;
  animation-delay: var(--delay, 0s), 0s;
}

@keyframes live-glow {
  0%, 100% { box-shadow: 0 0 8px rgba(255, 71, 87, 0.3); }
  50%       { box-shadow: 0 0 20px rgba(255, 71, 87, 0.7); }
}

/* ── Final card ── */
.bracket-card.final {
  border-color: var(--green);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--green) 30%, transparent);
  animation: slide-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) both,
             final-glow 2.5s ease-in-out infinite;
  animation-delay: var(--delay, 0s), 0s;
}

@keyframes final-glow {
  0%, 100% { box-shadow: 0 0 10px color-mix(in srgb, var(--green) 20%, transparent); }
  50%       { box-shadow: 0 0 28px color-mix(in srgb, var(--green) 50%, transparent); }
}

/* ── TBD ghost card ── */
.bracket-card.tbd {
  cursor: default;
  pointer-events: none;
  opacity: 0;
  animation: slide-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: var(--delay, 0s);
}

/* Shimmer sweep overlay */
.shimmer-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 40%,
    color-mix(in srgb, var(--green) 8%, transparent) 50%,
    transparent 60%
  );
  background-size: 200% 100%;
  animation: shimmer 2.8s ease-in-out infinite;
  animation-delay: calc(var(--delay, 0s) + 0.5s);
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Card content ── */
.bracket-time {
  font-size: 0.65rem;
  color: var(--muted);
  margin-bottom: 0.4rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bracket-team {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
}
.bracket-team:first-of-type { border-bottom: 1px solid var(--border); }

.b-flag { width: 18px; height: 13px; object-fit: cover; border-radius: 2px; flex-shrink: 0; }

.b-name {
  font-size: 0.78rem;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
}

.bracket-team.winner .b-name {
  color: var(--text);
  font-weight: 700;
}

.b-score {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text);
  flex-shrink: 0;
}

.live-badge {
  position: absolute;
  top: 4px;
  right: 6px;
  font-size: 0.6rem;
  font-weight: 700;
  color: #ff4757;
  letter-spacing: 0.05em;
  animation: blink 1.2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* TBD styles */
.tbd-flag {
  width: 18px;
  height: 13px;
  border-radius: 2px;
  background: var(--border);
  flex-shrink: 0;
}

.tbd-text { color: var(--muted) !important; font-style: italic; }
</style>
