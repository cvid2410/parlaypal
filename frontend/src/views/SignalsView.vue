<template>
  <div class="sig-screen">
    <div class="sect">
      <span v-if="auth.isPaid" class="livedot" />
      {{ auth.isPaid ? 'Live signals · soft leagues' : 'Locked on Free · upgrade to see picks' }}
      <button class="refresh" @click="load" :disabled="loading" title="Refresh">↻</button>
    </div>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="!loading && grouped.length === 0" class="empty">
      No live signals right now. Lines are efficient at the moment — check back soon.
    </p>

    <div class="grid">
      <div v-for="s in grouped" :key="s.id" class="sig" :class="{ locked: s.locked }">
        <div class="top">
          <span class="kind" :class="s.kind">{{ s.kind === 'arb' ? 'Arbitrage' : 'Value bet' }}</span>
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
          <div v-if="s.kind !== 'arb'" class="line">
            <span class="at">at</span><span class="bk">{{ s.book }}</span><span class="o">{{ s.odds }}</span>
          </div>
          <div class="why">{{ s.body }}</div>
          <div class="stats">
            <div class="stat"><div class="v green">{{ metric(s) }}</div><div class="k">{{ s.kind === 'arb' ? 'locked profit' : 'your edge' }}</div></div>
            <div v-if="s.kind !== 'arb'" class="stat"><div class="v">{{ s.fair_odds }}</div><div class="k">fair price</div></div>
            <div v-if="s.kind !== 'arb'" class="stat"><div class="v">{{ s.stake_pct }}%</div><div class="k">stake</div></div>
          </div>
        </template>

        <div v-else class="lockmask">
          <div class="t">Live signal — unlock the pick &amp; odds</div>
          <button class="u" @click="ui.openUpgrade()">Unlock with Pro</button>
        </div>
      </div>
    </div>

    <p class="foot">For entertainment, not financial advice. Bet responsibly — 1-800-GAMBLER.</p>
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
  home_logo?: string | null; away_logo?: string | null
}

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
function pickLabel(s: Signal) {
  return s.kind === 'arb' ? 'Win either way' : (s.pick || s.title || '')
}
function metric(s: Signal) {
  return s.kind === 'arb' ? `+${s.profit_pct}%` : `+${s.edge_pct}%`
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

.sig { border: 1px solid var(--hair); border-radius: 16px; padding: 20px; background: var(--panel); position: relative; transition: .18s; overflow: hidden; }
.sig:hover { border-color: var(--hair-2); transform: translateY(-1px); }
.top { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; margin-bottom: 15px; }
.kind { font-size: 10.5px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; padding: 4px 9px; border-radius: 100px; }
.kind.ev { background: var(--green-dim); color: var(--green); }
.kind.arb { background: var(--surface-2); color: var(--txt); border: 1px solid var(--hair-2); }
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
.why { font-size: 13px; line-height: 1.6; color: var(--txt-2); margin-top: 15px; }
.stats { display: flex; gap: 26px; margin-top: 16px; padding-top: 15px; border-top: 1px solid var(--hair); }
.stat .v { font-family: 'Spline Sans Mono', monospace; font-size: 16px; font-weight: 600; }
.stat .v.green { color: var(--green); }
.stat .k { font-size: 10px; color: var(--txt-3); text-transform: uppercase; letter-spacing: .06em; margin-top: 4px; font-weight: 700; }

.sig.locked { min-height: 200px; }
.sig.locked .pick, .sig.locked .fx { filter: blur(7px); opacity: .5; user-select: none; }
.lockmask { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 13px; }
.lockmask .t { font-size: 13px; color: var(--txt-2); font-weight: 500; text-align: center; padding: 0 28px; line-height: 1.5; }
.lockmask .u { background: var(--green); color: #04210f; border: none; font-weight: 800; font-size: 12.5px; padding: 10px 22px; border-radius: 100px; cursor: pointer; text-transform: uppercase; letter-spacing: .3px; }

.foot { color: var(--txt-3); font-size: 11px; margin-top: 24px; }
</style>
