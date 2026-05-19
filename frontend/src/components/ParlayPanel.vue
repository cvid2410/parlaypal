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

    <button v-if="parlay.picks.length" class="share-btn" @click="share">
      {{ copied ? '✓ Copied!' : 'Share Parlay' }}
    </button>

    <div v-if="parlay.picks.length" class="place-bet">
      <p class="place-bet-label">Ready to bet?</p>
      <div class="book-btns">
        <a
          v-for="book in books"
          :key="book.key"
          :href="book.url"
          target="_blank"
          rel="noopener noreferrer sponsored"
          class="book-btn"
        >
          {{ book.name }}
        </a>
      </div>
      <p class="disclaimer">21+ only. Gambling problem? Call 1-800-GAMBLER.</p>
    </div>

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

      <button class="save-btn" @click="save">
        {{ saved ? '✓ Saved!' : 'Save Parlay' }}
      </button>
    </div>

    <!-- History -->
    <div v-if="parlay.history.length" class="history">
      <div class="history-header">
        <button class="history-toggle" @click="historyOpen = !historyOpen">
          Past Parlays ({{ parlay.history.length }}) {{ historyOpen ? '▲' : '▼' }}
        </button>
        <button class="clear-history-btn" @click="parlay.clearHistory()">Clear</button>
      </div>

      <div v-if="historyOpen" class="history-list">
        <div v-for="entry in parlay.history" :key="entry.id" class="history-entry">
          <div class="history-meta">
            <span class="history-date">{{ formatDate(entry.date) }}</span>
            <span class="history-status" :class="entry.status">{{ entry.status }}</span>
          </div>
          <div class="history-picks">
            {{ entry.picks.map(p => p.label).join(' · ') }}
          </div>
          <div class="history-payout">
            ${{ entry.stake }} → <strong>${{ entry.payout.toFixed(2) }}</strong>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useParlayStore } from '../stores/parlay'

const parlay = useParlayStore()
const copied = ref(false)
const saved = ref(false)
const historyOpen = ref(false)

async function share() {
  const encoded = btoa(JSON.stringify(parlay.picks))
  const url = `${window.location.origin}/parlay?p=${encoded}`
  await navigator.clipboard.writeText(url)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function save() {
  parlay.saveCurrent()
  historyOpen.value = true
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  }).format(new Date(iso))
}

interface Book { key: string; name: string; url: string }

const FALLBACKS: Book[] = [
  { key: 'draftkings', name: 'DraftKings', url: 'https://sportsbook.draftkings.com' },
  { key: 'fanduel',    name: 'FanDuel',    url: 'https://sportsbook.fanduel.com' },
  { key: 'betmgm',     name: 'BetMGM',     url: 'https://sports.betmgm.com' },
]

const books = ref<Book[]>(FALLBACKS)

onMounted(async () => {
  try {
    const res = await fetch('/api/config')
    if (!res.ok) return
    const data = await res.json()
    books.value = data.books.map((b: Book & { url: string }) => ({
      key: b.key,
      name: b.name,
      url: b.url && b.url !== '#' ? b.url : FALLBACKS.find(f => f.key === b.key)?.url ?? b.url,
    }))
  } catch { /* keep fallbacks */ }
})

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

.share-btn {
  width: 100%;
  padding: 7px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.8rem;
  color: var(--muted);
  margin-bottom: 0.75rem;
  transition: color 0.15s, border-color 0.15s;
}
.share-btn:hover { color: var(--text); border-color: var(--text); }

.place-bet {
  border-top: 1px solid var(--border);
  padding-top: 1rem;
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.place-bet-label {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.book-btns { display: flex; gap: 6px; }

.book-btn {
  flex: 1;
  text-align: center;
  padding: 8px 4px;
  background: var(--green);
  color: #000;
  font-size: 0.78rem;
  font-weight: 700;
  border-radius: 6px;
  transition: opacity 0.15s;
}
.book-btn:hover { opacity: 0.85; }

.disclaimer { font-size: 0.68rem; color: var(--muted); text-align: center; }

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

.save-btn {
  width: 100%;
  margin-top: 0.75rem;
  padding: 8px;
  border: 1px solid var(--green);
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--green);
  transition: background 0.15s;
}
.save-btn:hover { background: color-mix(in srgb, var(--green) 10%, transparent); }

.history {
  border-top: 1px solid var(--border);
  padding-top: 0.875rem;
  margin-top: 0.875rem;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.history-toggle {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--muted);
  transition: color 0.15s;
}
.history-toggle:hover { color: var(--text); }

.clear-history-btn {
  font-size: 0.72rem;
  color: var(--muted);
  transition: color 0.15s;
}
.clear-history-btn:hover { color: #ff4757; }

.history-list { display: flex; flex-direction: column; gap: 8px; }

.history-entry {
  background: var(--dark);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.history-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-date { font-size: 0.72rem; color: var(--muted); }

.history-status {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
}
.history-status.pending { color: var(--muted); background: var(--border); }
.history-status.won { color: var(--green); background: color-mix(in srgb, var(--green) 15%, transparent); }
.history-status.lost { color: #ff4757; background: rgba(255,71,87,0.12); }

.history-picks {
  font-size: 0.78rem;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-payout { font-size: 0.75rem; color: var(--muted); }
.history-payout strong { color: var(--text); }
</style>
