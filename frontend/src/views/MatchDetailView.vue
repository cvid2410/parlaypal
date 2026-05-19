<template>
  <div class="match-detail">
    <button class="back-btn" @click="router.back()">← Back to Schedule</button>

    <div v-if="matchesStore.loading" class="state-msg">Loading match...</div>
    <div v-else-if="!match" class="state-msg error">Match not found.</div>

    <template v-else>
      <!-- Match header -->
      <div class="match-header">
        <div class="header-meta">
          <span class="group-tag">{{ match.group }}</span>
          <span v-if="match.status !== 'scheduled'" class="status-tag" :class="match.status">
            {{ match.status === 'live' ? 'LIVE' : 'FT' }}
          </span>
        </div>

        <div class="teams-row">
          <div class="team">
            <img :src="match.home_flag" :alt="match.home_team" class="flag" />
            <span class="team-name">{{ match.home_team }}</span>
          </div>
          <div class="vs-block">
            <template v-if="match.home_score != null">
              <span class="live-score">{{ match.home_score }} – {{ match.away_score }}</span>
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

        <div class="match-meta">
          <span>{{ matchesStore.formatMatchTime(match.date) }} {{ matchesStore.selectedTimezone }}</span>
          <span class="separator">·</span>
          <span>{{ match.venue }}, {{ match.city }}</span>
        </div>
      </div>

      <!-- Winner picks -->
      <section class="odds-section">
        <div class="section-title-row">
          <h2 class="section-title">Match Winner</h2>
          <button class="info-btn" @click="vigInfoOpen = !vigInfoOpen">?</button>
        </div>

        <div v-if="vigInfoOpen" class="vig-explainer">
          <p><strong>What is "Fair"?</strong> Sportsbooks bake a profit margin (the "vig") into every line — the three implied probabilities always add up to more than 100%. <em>Fair</em> strips that out and shows you the true odds.</p>
          <p class="explainer-tip"><strong>Color guide:</strong> <span class="vig-good">Green</span> = good price (low vig, close to fair). <span class="vig-ok">Yellow</span> = slight overcharge. <span class="vig-bad">Red</span> = steep price — the book is taking a large cut on this outcome. When you see red, shop other books or consider skipping.</p>
        </div>

        <div v-if="oddsLoading" class="odds-skeleton-row" />
        <div v-else-if="h2hByBook.length === 0" class="no-odds">Odds not yet available.</div>
        <div v-else class="book-rows">
          <div v-for="row in h2hByBook" :key="row.book" class="book-row">
            <span class="book-label">{{ BOOK_NAMES[row.book] ?? row.book }}</span>
            <div class="odds-btns">
              <div v-for="(line, i) in row.lines" :key="line.selection" class="odds-btn-col">
                <OddsButton
                  :match-id="match.id"
                  market="h2h"
                  :selection="line.selection"
                  :odds="line.odds"
                  :book="row.book"
                  :label="`${formatSelection(line.selection)} (${line.odds})`"
                />
                <span
                  class="no-vig"
                  :class="vigClass(noVigOdds(row.lines)[i].vig)"
                  :title="vigLabel(noVigOdds(row.lines)[i].vig)"
                >
                  Fair: {{ noVigOdds(row.lines)[i].odds }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Props tabs -->
      <section class="odds-section">
        <h2 class="section-title" style="margin-bottom:0.875rem">Prop Bets</h2>
        <div class="tabs">
          <button
            v-for="tab in TABS"
            :key="tab.key"
            class="tab-btn"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="tab-content">
          <template v-for="tab in TABS" :key="tab.key">
            <div v-if="activeTab === tab.key">
              <div v-if="oddsLoading" class="odds-skeleton-row" />
              <template v-else>
                <template v-for="market in tab.markets" :key="market">
                  <div v-if="propsByBook(match.id, market).length > 0" class="market-group">
                    <p class="market-label">{{ MARKET_LABELS[market] ?? market }}</p>
                    <div class="book-rows">
                      <div v-for="row in propsByBook(match.id, market)" :key="row.book" class="book-row">
                        <span class="book-label">{{ BOOK_NAMES[row.book] ?? row.book }}</span>
                        <div class="odds-btns">
                          <OddsButton
                            v-for="line in row.lines"
                            :key="line.selection + String(line.point)"
                            :match-id="match.id"
                            :market="market"
                            :selection="line.selection + (line.point != null ? `_${line.point}` : '')"
                            :odds="line.odds"
                            :book="row.book"
                            :label="propLabel(market, line)"
                                      />
                        </div>
                      </div>
                    </div>
                  </div>
                </template>
                <div v-if="tab.markets.every(m => propsByBook(matchId, m).length === 0)" class="no-odds">
                  Odds not yet available for {{ tab.label }}.
                </div>
              </template>
            </div>
          </template>
        </div>
      </section>

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

      <!-- Affiliate CTAs -->
      <AffiliateCTAs class="affiliate-strip" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMatchesStore } from '../stores/matches'
import { useOddsStore, type OddsLine } from '../stores/odds'
import OddsButton from '../components/OddsButton.vue'
import AffiliateCTAs from '../components/AffiliateCTAs.vue'

const route = useRoute()
const router = useRouter()
const matchesStore = useMatchesStore()
const oddsStore = useOddsStore()

const activeTab = ref('goals')
const vigInfoOpen = ref(false)

const TABS = [
  { key: 'goals', label: 'Goals', markets: ['totals', 'btts'] },
  { key: 'corners', label: 'Corners', markets: ['corners'] },
  { key: 'shots', label: 'Shots on Target', markets: ['player_shots_on_target'] },
  { key: 'cards', label: 'Cards', markets: ['player_cards'] },
] as const

const BOOK_NAMES: Record<string, string> = {
  draftkings: 'DraftKings',
  fanduel: 'FanDuel',
  betmgm: 'BetMGM',
}

const MARKET_LABELS: Record<string, string> = {
  totals: 'Total Goals',
  btts: 'Both Teams to Score',
  corners: 'Corners',
  player_shots_on_target: 'Shots on Target',
  player_cards: 'Cards',
}

const matchId = computed(() => Number(route.params.id))

const match = computed(() =>
  matchesStore.matches.find(m => m.id === matchId.value) ?? null
)

const oddsLoading = computed(() => !!oddsStore.loading[matchId.value])

function groupByBook(lines: OddsLine[]): { book: string; lines: OddsLine[] }[] {
  const map: Record<string, OddsLine[]> = {}
  for (const line of lines) {
    if (!map[line.book]) map[line.book] = []
    map[line.book].push(line)
  }
  return Object.entries(map).map(([book, lines]) => ({ book, lines }))
}

const h2hByBook = computed(() => groupByBook(oddsStore.getOdds(matchId.value, 'h2h')))

function propsByBook(id: number, market: string) {
  return groupByBook(oddsStore.getOdds(id, market))
}

function formatSelection(selection: string): string {
  if (!match.value) return selection
  const home = match.value.home_team.toLowerCase().replace(/\s+/g, '_')
  const away = match.value.away_team.toLowerCase().replace(/\s+/g, '_')
  if (selection === home) return match.value.home_team
  if (selection === away) return match.value.away_team
  if (selection === 'draw') return 'Draw'
  return selection.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function toImplied(american: string): number {
  const n = parseInt(american, 10)
  return n > 0 ? 100 / (n + 100) : Math.abs(n) / (Math.abs(n) + 100)
}

function toAmerican(prob: number): string {
  if (prob >= 0.5) return `-${Math.round(prob / (1 - prob) * 100)}`
  return `+${Math.round((1 - prob) / prob * 100)}`
}

function noVigOdds(lines: OddsLine[]): { odds: string; vig: number }[] {
  const implied = lines.map(l => toImplied(l.odds))
  const total = implied.reduce((a, b) => a + b, 0)
  return implied.map((imp) => {
    const fair = imp / total
    const vig = imp - fair  // how much extra the book charges on this outcome
    return { odds: toAmerican(fair), vig }
  })
}

function vigClass(vig: number): string {
  if (vig < 0.02) return 'vig-good'
  if (vig < 0.04) return 'vig-ok'
  return 'vig-bad'
}

function vigLabel(vig: number): string {
  if (vig < 0.02) return 'good price'
  if (vig < 0.04) return 'slight overcharge'
  return 'steep price'
}

function propLabel(_market: string, line: OddsLine): string {
  const sel = line.selection.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  if (line.point != null) return `${sel} ${line.point} (${line.odds})`
  return `${sel} (${line.odds})`
}

onMounted(async () => {
  if (matchesStore.matches.length === 0) await matchesStore.loadMatches()
  await oddsStore.fetchOdds(matchId.value)
})
</script>

<style scoped>
.match-detail { display: flex; flex-direction: column; gap: 1.25rem; }

.back-btn {
  align-self: flex-start;
  font-size: 0.85rem;
  color: var(--muted);
  padding: 4px 0;
  transition: color 0.15s;
}
.back-btn:hover { color: var(--text); }

.state-msg { color: var(--muted); padding: 2rem 0; }
.state-msg.error { color: #ff4757; }

/* Match header */
.match-header {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.header-meta { display: flex; gap: 0.5rem; align-items: center; }

.group-tag {
  font-size: 0.75rem;
  color: var(--muted);
  background: var(--dark);
  padding: 2px 8px;
  border-radius: 4px;
}

.status-tag {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}
.status-tag.live { color: #ff4757; background: rgba(255, 71, 87, 0.12); }
.status-tag.finished { color: var(--muted); background: var(--dark); }

.teams-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.team {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex: 1;
  min-width: 0;
}
.team.away { flex-direction: row-reverse; }

.flag { width: 36px; height: 26px; object-fit: cover; border-radius: 3px; flex-shrink: 0; }
.team-name { font-size: 1.1rem; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.vs-block { flex-shrink: 0; text-align: center; }
.vs { color: var(--muted); font-size: 0.85rem; }
.live-score { font-size: 1.4rem; font-weight: 800; color: var(--text); letter-spacing: 0.04em; }

.match-meta {
  display: flex;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--muted);
  flex-wrap: wrap;
}
.separator { color: var(--border); }

/* Odds sections */
.odds-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.875rem;
}

.section-title { font-size: 0.95rem; font-weight: 700; }

.info-btn {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1px solid var(--border);
  font-size: 0.65rem;
  color: var(--muted);
  line-height: 1;
  flex-shrink: 0;
  transition: border-color 0.15s, color 0.15s;
}
.info-btn:hover { border-color: var(--text); color: var(--text); }

.vig-explainer {
  background: var(--dark);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.75rem;
  margin-bottom: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--muted);
  line-height: 1.5;
}

.vig-explainer strong { color: var(--text); }
.vig-explainer em { color: var(--green); font-style: normal; }

.explainer-tip { padding-top: 0.5rem; border-top: 1px solid var(--border); }

.odds-skeleton-row {
  height: 52px;
  background: var(--dark);
  border-radius: 6px;
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.no-odds { font-size: 0.85rem; color: var(--muted); padding: 0.5rem 0; }

.book-rows { display: flex; flex-direction: column; gap: 0.5rem; }

.book-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--dark);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  flex-wrap: wrap;
}

.book-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--muted);
  min-width: 80px;
  flex-shrink: 0;
}

.odds-btns { display: flex; gap: 6px; flex-wrap: wrap; }

.odds-btn-col { display: flex; flex-direction: column; align-items: center; gap: 3px; }

.no-vig { font-size: 0.65rem; white-space: nowrap; font-weight: 600; }
.vig-good { color: var(--green); }
.vig-ok   { color: #f5a623; }
.vig-bad  { color: #ff4757; }

/* Tabs */
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 0.875rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.5rem;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.tabs::-webkit-scrollbar { display: none; }

.tab-btn {
  font-size: 0.82rem;
  color: var(--muted);
  padding: 5px 12px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--text); background: var(--border); font-weight: 600; }

.market-group { margin-bottom: 0.875rem; }
.market-group:last-child { margin-bottom: 0; }

.market-label {
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 600;
  margin-bottom: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Affiliate strip */
.affiliate-strip { margin-top: 0.25rem; }

.ad-unit { min-height: 90px; }

/* Mobile */
@media (max-width: 600px) {
  .team-name { font-size: 0.88rem; }
  .flag { width: 24px; height: 17px; }
  .live-score { font-size: 1.1rem; }
  .teams-row { gap: 0.4rem; }
  .book-row { gap: 0.5rem; }
  .book-label { min-width: 60px; font-size: 0.68rem; }
  .tab-btn { font-size: 0.78rem; padding: 5px 10px; white-space: nowrap; }
  .match-meta { flex-direction: column; gap: 2px; }
  .separator { display: none; }
  .match-header { padding: 1rem; }
}
</style>
