<template>
  <div class="sig-screen">
    <div class="sect">
      <span v-if="auth.isPaid" class="livedot" />
      {{ auth.isPaid ? 'Live signals · soft leagues' : 'Locked on Free · upgrade to see picks' }}
      <button class="refresh" @click="load" :disabled="loading" title="Refresh" aria-label="Refresh signals"><span aria-hidden="true">↻</span></button>
    </div>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="!loading && !error && grouped.length === 0" class="empty">
      No live signals right now. Lines are efficient at the moment - check back soon.
    </p>

    <!-- loading skeletons -->
    <div v-if="loading && grouped.length === 0" class="grid" aria-hidden="true">
      <div v-for="n in 4" :key="n" class="sig">
        <div class="sk" style="width: 92px; height: 21px; border-radius: 100px" />
        <div class="sk" style="width: 72%; height: 26px; margin-top: 16px" />
        <div class="sk" style="width: 46%; height: 13px; margin-top: 10px" />
        <div class="sk" style="width: 100%; height: 66px; margin-top: 16px; border-radius: 12px" />
        <div class="sk" style="width: 100%; height: 38px; margin-top: 15px" />
      </div>
    </div>

    <div class="grid">
      <div v-for="s in grouped" :key="s.id" class="sig" :class="[s.kind, { locked: s.locked }]">
        <div class="top">
          <span class="kind" :class="s.kind">{{ kindLabel(s) }}</span>
          <span class="lg">{{ s.league }} · {{ s.country }}</span>
          <span v-if="s.count > 1" class="reups" title="re-alerted as the edge improved">↑ {{ s.count }}×</span>
          <span class="ago">{{ ago(s.age_seconds) }}</span>
        </div>

        <div class="pick">{{ s.locked ? 'Locked pick' : pickLabel(s) }}</div>
        <div class="fx">
          <img v-if="s.home_logo" :src="s.home_logo" class="crest" loading="lazy" alt="" />
          <img v-if="s.away_logo" :src="s.away_logo" class="crest" loading="lazy" alt="" />
          <span>{{ s.fixture }}</span>
        </div>

        <template v-if="!s.locked">
          <div v-if="s.ticket" class="ticket">
            <div class="tk-h">Your bet</div>
            <template v-if="s.ticket.type === 'single'">
              <div v-for="(r, i) in s.ticket.rows" :key="i" class="tk-row">
                <span class="tk-k">{{ r.label }}</span><span class="tk-v">{{ r.value }}</span>
              </div>
            </template>
            <template v-else>
              <div v-for="(leg, i) in s.ticket.legs" :key="i" class="tk-leg">
                <div class="tk-leg-top"><span class="tk-pick">{{ leg.pick }}</span><span class="tk-odds">{{ leg.odds }}</span></div>
                <div class="tk-leg-sub">{{ leg.book }} · stake {{ leg.stake }}</div>
              </div>
              <div class="tk-note">{{ s.ticket.note }}</div>
            </template>
          </div>
          <div class="why">{{ s.body }}</div>
          <div class="stats">
            <div class="stat hero"><div class="v">+{{ s.edge_pct }}%</div><div class="k">{{ metricLabel(s) }}</div></div>
            <div v-if="priced(s)" class="stat"><div class="v">{{ s.fair_odds }}</div><div class="k">fair price</div></div>
            <div v-if="priced(s)" class="stat"><div class="v">{{ s.stake_pct }}%</div><div class="k">stake</div></div>
          </div>
          <RouterLink v-if="s.fixture_id" :to="`/lines/${s.fixture_id}`" class="compare">
            <span>Compare prices across books</span><span class="arr" aria-hidden="true">→</span>
          </RouterLink>
        </template>

        <div v-else class="lockmask">
          <div class="t">Live signal - unlock the pick &amp; odds</div>
          <button class="u" @click="ui.openUpgrade()">Unlock with Pro</button>
        </div>
      </div>
    </div>

    <p class="foot">For entertainment, not financial advice. Bet responsibly - 1-800-GAMBLER.</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useUiStore } from '../stores/ui'

interface Signal {
  id: number; kind: string; league: string; country: string; fixture: string
  age_seconds: number; locked: boolean; title?: string; body?: string
  pick?: string; book?: string; odds?: string; fair_odds?: string
  edge_pct?: number; stake_pct?: number; profit_pct?: number; count?: number
  home_logo?: string | null; away_logo?: string | null; fixture_id?: string
  ticket?: Ticket
}
interface TicketRow { label: string; value: string }
interface TicketLeg { book: string; pick: string; odds: string; stake: string }
interface Ticket { type: 'single' | 'multi'; rows?: TicketRow[]; legs?: TicketLeg[]; note?: string }

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const route = useRoute()
const signals = ref<Signal[]>([])
const loading = ref(false)
const error = ref('')

// Collapse re-alerts of the same pick into one card with a re-up count.
const grouped = computed<(Signal & { count: number })[]>(() => {
  const map = new Map<string, Signal & { count: number }>()
  for (const s of signals.value) {
    const key = s.locked ? `${s.fixture}` : `${s.fixture}|${s.pick}`
    const ex = map.get(key)
    if (!ex) { map.set(key, { ...s, count: 1 }); continue }
    const better = s.locked ? s.age_seconds < ex.age_seconds : (s.edge_pct ?? 0) > (ex.edge_pct ?? 0)
    map.set(key, { ...(better ? s : ex), count: ex.count + 1 })
  }
  return [...map.values()]
})

function ago(sec: number) {
  if (sec < 60) return 'just now'
  const m = Math.floor(sec / 60)
  return m < 60 ? `${m} min ago` : `${Math.floor(m / 60)}h ago`
}
const priced = (s: Signal) => s.kind === 'ev' || s.kind === 'promo'
function kindLabel(s: Signal) {
  return ({ arb: 'Arbitrage', middle: 'Middle', promo: 'Boost' } as Record<string, string>)[s.kind] || 'Value bet'
}
function pickLabel(s: Signal) {
  if (s.kind === 'arb') return 'Win either way'
  if (s.kind === 'middle') return 'Middle'
  return s.pick || s.title || ''
}
function metricLabel(s: Signal) {
  return ({ arb: 'locked profit', middle: 'middle upside', promo: 'boost edge' } as Record<string, string>)[s.kind] || 'your edge'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await auth.authFetch('/signals')
    if (res.status === 401) { router.push('/login'); return }
    if (!res.ok) throw new Error('Failed to load signals')
    signals.value = (await res.json()).signals
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// Re-fetch when the tier changes (dev upgrade via the modal, or Stripe return) so cards
// flip between locked teasers and full picks.
watch(() => auth.tier, () => load())

onMounted(async () => {
  if (!auth.isAuthed) { router.push('/login'); return }
  if (route.query.upgraded) await auth.fetchMe() // tier may have changed via Stripe webhook
  load()
})
</script>

<style scoped>
.sig-screen { color: var(--txt); }
.sect { font-size: 11px; color: var(--txt-3); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 0 0 16px; display: flex; align-items: center; gap: 8px; }
.sect .livedot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); }
.refresh { margin-left: auto; background: none; border: 1px solid var(--hair); color: var(--txt-2); border-radius: 8px; padding: 3px 10px; cursor: pointer; font-size: 13px; }
.err { color: #ff5a52; font-size: 13px; padding: 6px 0; }
.empty { color: var(--txt-2); font-size: 13.5px; padding: 14px 0; line-height: 1.5; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 16px; }

.sig { border: 1px solid var(--hair); border-radius: 16px; padding: 20px 20px 20px 23px; background: var(--panel); position: relative; transition: transform .18s, border-color .18s, box-shadow .18s; overflow: hidden; }
.sig:hover { border-color: var(--hair-2); transform: translateY(-2px); box-shadow: 0 8px 26px rgba(0, 0, 0, .38); }
/* kind accent - a thin colored spine on the left edge */
.sig::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent, var(--hair-2)); opacity: .9; }
.sig.ev { --accent: var(--green); }
.sig.arb { --accent: var(--hair-2); }
.sig.middle { --accent: #5cb3ff; }
.sig.promo { --accent: #ffc94d; }
.top { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; margin-bottom: 15px; }
.kind { font-size: 10.5px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; padding: 4px 9px; border-radius: 100px; }
.kind.ev { background: var(--green-dim); color: var(--green); }
.kind.arb { background: var(--surface-2); color: var(--txt); border: 1px solid var(--hair-2); }
.kind.middle { background: #0c2536; color: #5cb3ff; }
.kind.promo { background: #3a2f08; color: #ffc94d; }
.lg { font-size: 12px; color: var(--txt-3); }
.reups { font-size: 9.5px; font-weight: 700; color: var(--green); border: 1px solid var(--green-dim); padding: 2px 6px; border-radius: 100px; }
.ago { margin-left: auto; font-family: 'Spline Sans Mono', monospace; font-size: 12px; color: var(--txt-3); }
.pick { font-size: 22px; font-weight: 800; letter-spacing: -.025em; line-height: 1.12; }
.fx { font-size: 12.5px; color: var(--txt-3); margin-top: 8px; display: flex; align-items: center; gap: 6px; }
.fx .crest { width: 18px; height: 18px; object-fit: contain; }
.fx .crest + .crest { margin-left: -4px; }
.line { display: flex; align-items: baseline; gap: 9px; margin-top: 16px; padding-top: 15px; border-top: 1px solid var(--hair); }
.line .at { font-size: 12.5px; color: var(--txt-3); }
.line .bk { font-size: 13.5px; font-weight: 700; }
.line .o { margin-left: auto; font-family: 'Spline Sans Mono', monospace; font-size: 22px; font-weight: 600; color: var(--green); }
.ticket { margin-top: 16px; padding: 14px; border: 1px solid var(--hair-2); border-radius: 12px; background: var(--surface-2); }
.tk-h { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; color: var(--txt-3); margin-bottom: 10px; }
.tk-row { display: flex; align-items: baseline; justify-content: space-between; padding: 4px 0; }
.tk-k { font-size: 12px; color: var(--txt-3); }
.tk-v { font-size: 13.5px; font-weight: 700; text-align: right; }
.tk-leg { padding: 7px 0; border-top: 1px solid var(--hair); }
.tk-leg:first-of-type { border-top: none; }
.tk-leg-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.tk-pick { font-size: 13.5px; font-weight: 700; }
.tk-odds { font-family: 'Spline Sans Mono', monospace; font-size: 15px; font-weight: 600; color: var(--green); }
.tk-leg-sub { font-size: 11.5px; color: var(--txt-3); margin-top: 2px; }
.tk-note { font-size: 11.5px; color: var(--txt-2); line-height: 1.5; margin-top: 9px; padding-top: 9px; border-top: 1px solid var(--hair); }
.why { font-size: 13px; line-height: 1.6; color: var(--txt-2); margin-top: 15px; }
.stats { display: flex; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--hair); }
.stat { flex: 1; min-width: 0; background: var(--bg); border: 1px solid var(--hair); border-radius: 11px; padding: 11px 12px; }
.stat .v { font-family: 'Spline Sans Mono', monospace; font-size: 17px; font-weight: 600; line-height: 1; }
.stat .k { font-size: 9.5px; color: var(--txt-3); text-transform: uppercase; letter-spacing: .06em; margin-top: 7px; font-weight: 700; white-space: nowrap; }
.stat.hero { background: var(--green-dim); border-color: transparent; }
.stat.hero .v { color: var(--green); }
.stat.hero .k { color: var(--green); opacity: .85; }

.sig.locked { min-height: 200px; }
.sig.locked .pick, .sig.locked .fx { filter: blur(7px); opacity: .5; user-select: none; }
.lockmask { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 13px; }
.lockmask .t { font-size: 13px; color: var(--txt-2); font-weight: 500; text-align: center; padding: 0 28px; line-height: 1.5; }
.lockmask .u { background: var(--green); color: #04210f; border: none; font-weight: 800; font-size: 12.5px; padding: 10px 22px; border-radius: 100px; cursor: pointer; text-transform: uppercase; letter-spacing: .3px; }

.compare { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; padding: 11px 14px; border: 1px solid var(--hair); border-radius: 11px; font-size: 12.5px; font-weight: 600; color: var(--txt-2); transition: color .15s, border-color .15s, background .15s; }
.compare:hover { color: var(--green); border-color: var(--green-dim); background: var(--green-dim); }
.compare .arr { transition: transform .15s; }
.compare:hover .arr { transform: translateX(3px); }
.foot { color: var(--txt-3); font-size: 11px; margin-top: 24px; }
</style>
