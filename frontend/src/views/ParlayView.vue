<template>
  <div class="parlay-page">
    <h1 class="page-title">My Parlay</h1>
    <div class="layout">
      <ParlayPanel class="panel" />
      <div class="cta-area">
        <AffiliateCTAs />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import ParlayPanel from '../components/ParlayPanel.vue'
import AffiliateCTAs from '../components/AffiliateCTAs.vue'
import { useParlayStore, type Pick } from '../stores/parlay'

const route = useRoute()
const parlay = useParlayStore()

onMounted(() => {
  const p = route.query.p as string | undefined
  if (!p || parlay.picks.length > 0) return
  try {
    const picks: Pick[] = JSON.parse(atob(p))
    picks.forEach(pick => parlay.addPick(pick))
  } catch { /* malformed URL — ignore */ }
})
</script>

<style scoped>
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.25rem; }

.layout {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 1.25rem;
  align-items: start;
}

@media (max-width: 768px) {
  .layout { grid-template-columns: 1fr; }
}
</style>
