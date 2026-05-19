<template>
  <div>
    <div class="schedule-header">
      <div>
        <h1 class="page-title">WC 2026 Schedule</h1>
        <p class="subtitle">{{ store.filtered.length }} match{{ store.filtered.length === 1 ? '' : 'es' }}</p>
      </div>
      <TimezoneToggle />
    </div>

    <GroupFilter class="group-filter" />

    <div v-if="store.loading" class="match-grid">
      <div v-for="i in 6" :key="i" class="skeleton-card" />
    </div>

    <p v-else-if="store.error" class="error-msg">
      Failed to load matches. Please try again.
    </p>

    <div v-else-if="store.filtered.length === 0" class="empty-msg">
      No matches for this group yet.
    </div>

    <template v-else>
      <template v-for="(group, gi) in groupedByDate" :key="group.date">
        <h2 class="date-header animate-header" :style="`--gi: ${gi}`">{{ group.label }}</h2>
        <div class="match-grid">
          <MatchCard
            v-for="(match, ci) in group.matches"
            :key="match.id"
            :match="match"
            :style="`--delay: ${(gi * 0.08 + ci * 0.06).toFixed(2)}s`"
            class="animate-card"
          />
        </div>
      </template>
    </template>

    <!-- AdSense unit — replace data-ad-slot with your slot ID -->
    <div class="ad-unit">
      <ins
        class="adsbygoogle"
        style="display:block"
        data-ad-client="ca-pub-2359818837116456"
        data-ad-slot="XXXXXXXXXX"
        data-ad-format="auto"
        data-full-width-responsive="true"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useMatchesStore } from '../stores/matches'
import { useOddsStore } from '../stores/odds'
import TimezoneToggle from '../components/TimezoneToggle.vue'
import GroupFilter from '../components/GroupFilter.vue'
import MatchCard from '../components/MatchCard.vue'

const store = useMatchesStore()
const oddsStore = useOddsStore()

const TZ_MAP: Record<string, string> = {
  ET: 'America/New_York',
  CT: 'America/Chicago',
  MT: 'America/Denver',
  PT: 'America/Los_Angeles',
}

const groupedByDate = computed(() => {
  const tz = TZ_MAP[store.selectedTimezone] || 'America/New_York'
  const map = new Map<string, typeof store.filtered>()
  for (const match of store.filtered) {
    const localDate = new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(new Date(match.date))
    if (!map.has(localDate)) map.set(localDate, [])
    map.get(localDate)!.push(match)
  }
  return Array.from(map.entries()).map(([date, matches]) => ({
    date,
    matches,
    label: new Intl.DateTimeFormat('en-US', {
      timeZone: tz, weekday: 'long', month: 'long', day: 'numeric',
    }).format(new Date(date + 'T12:00:00')),
  }))
})

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await store.loadMatches()
  oddsStore.fetchCardH2H()
  pollTimer = setInterval(() => {
    if (store.matches.some(m => m.status === 'live')) {
      store.loadMatches()
    }
  }, 60_000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.schedule-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.page-title { font-size: 1.5rem; font-weight: 700; }
.subtitle { color: var(--muted); font-size: 0.85rem; margin-top: 2px; }

.group-filter { margin-bottom: 1.25rem; }

.match-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 0.75rem;
}

.skeleton-card {
  height: 120px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.error-msg { color: #ff4757; padding: 2rem 0; }
.empty-msg { color: var(--muted); padding: 2rem 0; }

.date-header {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 1.25rem 0 0.6rem;
}

.date-header:first-of-type { margin-top: 0; }

.animate-header {
  animation: header-drop 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(var(--gi, 0) * 0.08s);
}

@keyframes header-drop {
  from { opacity: 0; transform: translateY(-5px); }
  to   { opacity: 1; transform: translateY(0); }
}

.animate-card {
  animation: card-in 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--delay, 0s);
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.ad-unit { margin-top: 1.5rem; }
</style>
