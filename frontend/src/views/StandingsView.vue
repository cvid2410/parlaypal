<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">WC 2026 Standings</h1>
      <p class="subtitle">Top 2 per group advance to Round of 32</p>
    </div>

    <div v-if="loading" class="groups-grid">
      <div v-for="i in 12" :key="i" class="skeleton-group" />
    </div>

    <p v-else-if="error" class="error-msg">Failed to load standings. Please try again.</p>

    <div v-else-if="groups.length === 0" class="empty-msg">
      Standings will appear once the tournament begins on June 11, 2026.
    </div>

    <div v-else class="groups-grid">
      <div
        v-for="(group, gi) in groups"
        :key="group.group"
        class="group-card animate-card"
        :style="`--delay: ${(gi * 0.07).toFixed(2)}s`"
      >
        <h2 class="group-title">{{ group.group }}</h2>
        <table class="standings-table">
          <thead>
            <tr>
              <th class="col-team">Team</th>
              <th>P</th>
              <th>W</th>
              <th>D</th>
              <th>L</th>
              <th>GD</th>
              <th>Pts</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(entry, i) in group.entries"
              :key="entry.team"
              :class="{ advancing: i < 2 }"
            >
              <td class="col-team">
                <img :src="entry.logo" :alt="entry.team" class="team-logo" />
                <span class="team-name">{{ entry.team }}</span>
              </td>
              <td>{{ entry.played }}</td>
              <td>{{ entry.won }}</td>
              <td>{{ entry.drawn }}</td>
              <td>{{ entry.lost }}</td>
              <td>{{ entry.gd > 0 ? '+' + entry.gd : entry.gd }}</td>
              <td class="pts">{{ entry.points }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface StandingEntry {
  rank: number
  team: string
  logo: string
  played: number
  won: number
  drawn: number
  lost: number
  gf: number
  ga: number
  gd: number
  points: number
}

interface Group {
  group: string
  entries: StandingEntry[]
}

const groups = ref<Group[]>([])
const loading = ref(true)
const error = ref(false)

onMounted(async () => {
  try {
    const res = await fetch('/api/standings')
    if (!res.ok) throw new Error()
    groups.value = await res.json()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-header { margin-bottom: 1.5rem; }
.page-title { font-size: 1.5rem; font-weight: 700; }
.subtitle { color: var(--muted); font-size: 0.85rem; margin-top: 2px; }

.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(320px, 100%), 1fr));
  gap: 1rem;
}

.skeleton-group {
  height: 220px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.group-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
}

.group-card:hover {
  border-color: var(--green);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 200, 83, 0.1);
}

.animate-card {
  animation: card-in 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--delay, 0s);
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.group-title {
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  padding: 0.6rem 0.875rem;
  border-bottom: 1px solid var(--border);
}

.standings-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

thead tr { border-bottom: 1px solid var(--border); }

th {
  padding: 6px 8px;
  color: var(--muted);
  font-weight: 600;
  font-size: 0.72rem;
  text-align: center;
}

th.col-team { text-align: left; padding-left: 0.875rem; }

td {
  padding: 7px 8px;
  text-align: center;
  color: var(--text);
}

td.col-team {
  text-align: left;
  padding-left: 0.875rem;
  display: flex;
  align-items: center;
  gap: 7px;
}

tbody tr { border-bottom: 1px solid var(--border); }
tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: var(--dark); }

tbody tr.advancing { border-left: 3px solid var(--green); }

.team-logo { width: 20px; height: 20px; object-fit: contain; flex-shrink: 0; }
.team-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.pts { font-weight: 700; }

.error-msg { color: #ff4757; padding: 2rem 0; }
.empty-msg { color: var(--muted); padding: 2rem 0; line-height: 1.6; }
</style>
