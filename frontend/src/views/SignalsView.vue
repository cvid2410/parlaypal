<template>
  <div class="sig-screen">
    <div class="topbar">
      <div class="head">
        <span class="dot" /> Parlay<span class="g">Pal</span> Signals
      </div>
      <span class="badge" :class="auth.isPaid ? 'pro' : 'free'">{{ auth.tier }}</span>
    </div>

    <div class="sect">
      <template v-if="auth.isPaid"><span class="live" /> Live signals · soft leagues</template>
      <template v-else>Signals · <span class="gold">locked on Free</span></template>
      <button class="refresh" @click="load" :disabled="loading">↻</button>
    </div>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="!loading && signals.length === 0" class="empty">
      No live signals right now. Lines are efficient at the moment — check back soon.
    </p>

    <div
      v-for="s in signals"
      :key="s.id"
      class="card"
      :class="{ locked: s.locked }"
    >
      <div class="ribbon" :class="s.kind === 'arb' ? 'r-arb' : 'r-ev'" />
      <div class="chead">
        <span class="tag" :class="s.kind">{{ s.kind === 'arb' ? '★ Arbitrage' : 'Value Bet' }}</span>
        <span class="lgn">{{ s.league }} · {{ s.country }}</span>
        <span class="tm">{{ ago(s.age_seconds) }}</span>
      </div>

      <div class="pk">
        <div class="m">{{ s.locked ? '🔒 Locked pick' : pickLabel(s) }}</div>
        <div class="fx">{{ s.fixture }}</div>
      </div>

      <template v-if="!s.locked">
        <div v-if="s.kind !== 'arb'" class="bb">
          <div><div class="l">Bet at</div><div class="n">{{ s.book }}</div></div>
          <div class="od">{{ s.odds }}</div>
        </div>
        <div class="wy">{{ s.body }}</div>
        <div class="ft">
          <div class="me"><div class="v green">{{ metric(s) }}</div><div class="l">{{ s.kind === 'arb' ? 'locked profit' : 'your edge' }}</div></div>
          <div v-if="s.kind !== 'arb'" class="me"><div class="v">{{ s.fair_odds }}</div><div class="l">fair price</div></div>
          <div v-if="s.kind !== 'arb'" class="me"><div class="v">{{ s.stake_pct }}%</div><div class="l">stake</div></div>
        </div>
      </template>

      <div v-else class="lockover">
        <div class="ic">🔒</div>
        <div class="t">{{ s.title }}</div>
        <button class="b" @click="showUpgrade = true">Unlock with Pro</button>
      </div>
    </div>

    <p class="foot">For entertainment, not financial advice. Bet responsibly — 1-800-GAMBLER.</p>

    <!-- upgrade modal -->
    <div v-if="showUpgrade" class="modal" @click.self="showUpgrade = false">
      <div class="sheet">
        <h3>Unlock the edge</h3>
        <p class="ld">Free shows you the activity. <b>Pro</b> shows you the pick, the book, and the price — live.</p>
        <div class="plan" @click="choose('bettor')">
          <div class="pn">Bettor <span class="pr">$29<small>/mo</small></span></div>
          <div class="pd">All value bets live · every soft league · stake calculator</div>
        </div>
        <div class="plan feat" @click="choose('sharp')">
          <div class="tagm">★ most popular</div>
          <div class="pn">Sharp <span class="pr">$79<small>/mo</small></span></div>
          <div class="pd">Everything + arbs · instant push · custom alerts</div>
        </div>
        <button class="close" @click="showUpgrade = false">Maybe later</button>
        <p class="devnote">Dev build: this flips your tier instantly (Stripe checkout wires in next).</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface Signal {
  id: number; kind: string; league: string; country: string; fixture: string
  age_seconds: number; locked: boolean; title?: string; body?: string
  pick?: string; book?: string; odds?: string; fair_odds?: string
  edge_pct?: number; stake_pct?: number; profit_pct?: number
}

const auth = useAuthStore()
const router = useRouter()
const signals = ref<Signal[]>([])
const loading = ref(false)
const error = ref('')
const showUpgrade = ref(false)

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

async function choose(tier: string) {
  await auth.upgrade(tier)
  showUpgrade.value = false
  await load()
}

onMounted(() => {
  if (!auth.isAuthed) { router.push('/login'); return }
  load()
})
</script>

<style scoped>
.sig-screen { max-width: 460px; margin: 0 auto; padding: 12px 12px 40px; color: #eef3f2; font-family: 'Archivo', sans-serif; }
.topbar { display: flex; align-items: center; gap: 9px; padding: 8px 4px 14px; border-bottom: 1px solid #222d30; }
.head { font-family: 'Archivo Narrow', sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; font-size: 16px; }
.head .g { color: #1fd65f; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #1fd65f; box-shadow: 0 0 10px #1fd65f; }
.badge { margin-left: auto; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; padding: 4px 10px; border-radius: 20px; }
.badge.free { background: #1a2123; color: #8a9a9c; }
.badge.pro { background: #ffc94d; color: #241a00; }
.sect { font-size: 11px; color: #5f6f71; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 16px 4px 12px; display: flex; align-items: center; gap: 7px; }
.sect .gold { color: #ffc94d; }
.sect .live { width: 7px; height: 7px; border-radius: 50%; background: #ff5a52; }
.refresh { margin-left: auto; background: none; border: 1px solid #222d30; color: #8a9a9c; border-radius: 8px; padding: 2px 9px; cursor: pointer; }
.err { color: #ff5a52; font-size: 13px; padding: 6px 4px; }
.empty { color: #8a9a9c; font-size: 13px; padding: 14px 4px; line-height: 1.5; }

.card { background: #13191b; border: 1px solid #222d30; border-radius: 14px; margin-bottom: 11px; overflow: hidden; position: relative; }
.ribbon { height: 3px; }
.r-ev { background: #1fd65f; } .r-arb { background: #ffc94d; }
.chead { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; padding: 11px 13px 0; }
.tag { font-size: 9.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; padding: 3px 7px; border-radius: 5px; }
.tag.ev { background: #0e3f23; color: #1fd65f; } .tag.arb { background: #3a2f08; color: #ffc94d; }
.lgn { font-size: 10.5px; color: #8a9a9c; font-weight: 500; }
.tm { margin-left: auto; font-family: 'Spline Sans Mono', monospace; font-size: 10.5px; color: #8a9a9c; }
.pk { padding: 8px 13px 2px; }
.pk .m { font-size: 17px; font-weight: 800; line-height: 1.15; }
.pk .fx { font-size: 11.5px; color: #8a9a9c; margin-top: 3px; }
.bb { display: flex; align-items: center; gap: 10px; margin: 10px 13px 0; padding: 9px 11px; background: #171f21; border: 1px solid #222d30; border-radius: 10px; }
.bb .l { font-size: 9px; color: #5f6f71; text-transform: uppercase; letter-spacing: .5px; }
.bb .n { font-size: 13px; font-weight: 700; margin-top: 1px; }
.od { font-family: 'Spline Sans Mono', monospace; font-weight: 600; font-size: 19px; margin-left: auto; color: #1fd65f; }
.wy { padding: 10px 14px 0; font-size: 12.5px; line-height: 1.5; color: #c2ced0; }
.ft { display: flex; gap: 9px; padding: 11px 13px 13px; }
.me .v { font-family: 'Spline Sans Mono', monospace; font-weight: 600; font-size: 14px; }
.me .v.green { color: #1fd65f; }
.me .l { font-size: 9px; color: #5f6f71; text-transform: uppercase; letter-spacing: .5px; margin-top: 1px; }

.locked .pk .m { color: #5f6f71; }
.lockover { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 16px; }
.lockover .ic { font-size: 22px; }
.lockover .t { font-size: 13px; font-weight: 700; text-align: center; color: #c2ced0; }
.lockover .b { background: #ffc94d; color: #241a00; font-weight: 800; font-size: 12px; padding: 8px 18px; border-radius: 8px; border: none; cursor: pointer; text-transform: uppercase; }
.foot { text-align: center; color: #5f6f71; font-size: 10.5px; margin-top: 18px; line-height: 1.5; }

.modal { position: fixed; inset: 0; background: rgba(5,8,10,.86); display: flex; align-items: center; justify-content: center; padding: 18px; z-index: 50; }
.sheet { background: #0a0e0f; border: 1px solid #222d30; border-radius: 20px; padding: 20px 17px; width: 100%; max-width: 340px; }
.sheet h3 { font-size: 19px; font-weight: 800; text-align: center; }
.sheet .ld { text-align: center; color: #8a9a9c; font-size: 12.5px; margin: 6px 0 16px; line-height: 1.5; }
.sheet .ld b { color: #ffc94d; }
.plan { border: 1px solid #222d30; border-radius: 13px; padding: 13px; margin-bottom: 10px; cursor: pointer; }
.plan.feat { border-color: #ffc94d; background: #15120a; }
.plan .pn { font-size: 14px; font-weight: 800; display: flex; justify-content: space-between; }
.plan .pn .pr { font-family: 'Spline Sans Mono', monospace; color: #ffc94d; }
.plan .pd { font-size: 11.5px; color: #8a9a9c; margin-top: 4px; line-height: 1.4; }
.plan .tagm { font-size: 9px; font-weight: 800; color: #ffc94d; text-transform: uppercase; letter-spacing: .5px; }
.close { display: block; width: 100%; margin-top: 6px; background: none; border: none; color: #5f6f71; font-size: 12px; padding: 8px; cursor: pointer; }
.devnote { text-align: center; color: #5f6f71; font-size: 10px; margin-top: 4px; }
</style>
