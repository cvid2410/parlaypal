<template>
  <div>
    <div class="schedule-header">
      <div>
        <h1 class="page-title">WC 2026 Schedule</h1>
        <p class="subtitle">{{ store.filtered.length }} matches</p>
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

    <div v-else class="match-grid">
      <MatchCard v-for="match in store.filtered" :key="match.id" :match="match" />
    </div>

    <!-- AdSense unit — replace data-ad-slot with your slot ID -->
    <div class="ad-unit">
      <ins
        class="adsbygoogle"
        style="display:block"
        data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
        data-ad-slot="XXXXXXXXXX"
        data-ad-format="auto"
        data-full-width-responsive="true"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useMatchesStore } from '../stores/matches'
import TimezoneToggle from '../components/TimezoneToggle.vue'
import GroupFilter from '../components/GroupFilter.vue'
import MatchCard from '../components/MatchCard.vue'

const store = useMatchesStore()

onMounted(() => store.loadMatches())
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

.ad-unit { margin-top: 1.5rem; }
</style>
