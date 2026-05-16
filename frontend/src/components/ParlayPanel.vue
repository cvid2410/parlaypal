<template>
  <div class="parlay-panel">
    <div class="panel-header">
      <h2>My Parlay <span class="count">{{ parlay.picks.length }}</span></h2>
      <button v-if="parlay.picks.length" class="clear-btn" @click="parlay.clear()">Clear all</button>
    </div>

    <div v-if="parlay.picks.length === 0" class="empty">
      <p>Add picks from the schedule to build your parlay.</p>
    </div>

    <ul v-else class="picks-list">
      <li v-for="pick in parlay.picks" :key="pick.id" class="pick-row">
        <div class="pick-info">
          <span class="pick-label">{{ pick.label }}</span>
          <span class="pick-odds" :class="oddsClass(pick.odds)">{{ pick.odds }}</span>
        </div>
        <button class="remove-btn" @click="parlay.removePick(pick.id)" aria-label="Remove pick">×</button>
      </li>
    </ul>

    <div v-if="parlay.picks.length" class="calculator">
      <div class="stake-row">
        <span class="calc-label">Stake</span>
        <div class="stake-btns">
          <button
            v-for="s in parlay.STAKES"
            :key="s"
            class="stake-btn"
            :class="{ active: parlay.stake === s }"
            @click="parlay.setStake(s)"
          >
            ${{ s }}
          </button>
        </div>
      </div>

      <div class="calc-rows">
        <div class="calc-row">
          <span class="calc-label">Multiplier</span>
          <span class="calc-value">{{ parlay.multiplier.toFixed(2) }}×</span>
        </div>
        <div class="calc-row">
          <span class="calc-label">Payout</span>
          <span class="calc-value">${{ parlay.payout.toFixed(2) }}</span>
        </div>
        <div class="calc-row profit">
          <span class="calc-label">Profit</span>
          <span class="calc-value green">+${{ parlay.profit.toFixed(2) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useParlayStore } from '../stores/parlay'

const parlay = useParlayStore()

function oddsClass(odds: string) {
  return parseInt(odds, 10) > 0 ? 'positive' : 'negative'
}
</script>

<style scoped>
.parlay-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.panel-header h2 { font-size: 1rem; font-weight: 700; }

.count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--green);
  color: #000;
  font-size: 0.7rem;
  font-weight: 700;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  margin-left: 6px;
}

.clear-btn { font-size: 0.78rem; color: var(--muted); }
.clear-btn:hover { color: #ff4757; }

.empty { color: var(--muted); font-size: 0.85rem; padding: 1rem 0; text-align: center; }

.picks-list { list-style: none; display: flex; flex-direction: column; gap: 6px; margin-bottom: 1rem; }

.pick-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--dark);
  border-radius: 6px;
  padding: 8px 10px;
}

.pick-info { display: flex; flex-direction: column; gap: 2px; }
.pick-label { font-size: 0.82rem; }
.pick-odds { font-size: 0.78rem; font-weight: 700; }
.pick-odds.positive { color: var(--green); }
.pick-odds.negative { color: var(--muted); }

.remove-btn { color: var(--muted); font-size: 1.1rem; line-height: 1; padding: 2px 6px; }
.remove-btn:hover { color: #ff4757; }

.calculator { border-top: 1px solid var(--border); padding-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }

.stake-row { display: flex; flex-direction: column; gap: 6px; }
.stake-btns { display: flex; gap: 6px; }

.stake-btn {
  flex: 1;
  padding: 6px 4px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.82rem;
  color: var(--muted);
  transition: border-color 0.15s, color 0.15s;
}

.stake-btn.active { border-color: var(--green); color: var(--green); font-weight: 700; }

.calc-rows { display: flex; flex-direction: column; gap: 6px; }

.calc-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
}

.calc-row.profit { border-top: 1px solid var(--border); padding-top: 6px; }

.calc-label { color: var(--muted); }
.calc-value { font-weight: 700; }
.green { color: var(--green); }
</style>
