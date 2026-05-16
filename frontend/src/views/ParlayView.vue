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
import ParlayPanel from '../components/ParlayPanel.vue'
import AffiliateCTAs from '../components/AffiliateCTAs.vue'
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
