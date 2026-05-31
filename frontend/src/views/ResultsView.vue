<template>
  <div class="trk">
    <div class="sect-title">Results · verified track record</div>
    <p v-if="error" class="err">{{ error }}</p>

    <template v-else-if="data">
      <!-- hero -->
      <div class="hero">
        <div class="big" :class="pnlClass">{{ pnlUnits }}</div>
        <div class="sub">{{ heroSub }}</div>
      </div>

      <!-- bankroll curve -->
      <svg v-if="data.curve.length > 1" class="curve" viewBox="0 0 340 100" preserveAspectRatio="none">
        <defs>
          <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#1fd65f" stop-opacity=".35" />
            <stop offset="100%" stop-color="#1fd65f" stop-opacity="0" />
          </linearGradient>
        </defs>
        <polyline fill="none" stroke="#1fd65f" stroke-width="2.5" stroke-linejoin="round" :points="linePoints" />
        <polygon fill="url(#g)" :points="areaPoints" />
      </svg>

      <!-- stat boxes -->
      <div class="row3">
        <div class="box"><div class="v">{{ data.settled }}</div><div class="l">bets</div></div>
        <div class="box"><div class="v" :class="pnlClass">{{ data.roi_pct == null ? '—' : data.roi_pct + '%' }}</div><div class="l">ROI</div></div>
        <div class="box"><div class="v">{{ data.win_rate == null ? '—' : data.win_rate + '%' }}</div><div class="l">win rate</div></div>
      </div>

      <!-- CLV -->
      <div class="clv" v-if="data.clv_beat_pct != null">
        <div class="h"><span>You beat the closing line</span><b>{{ data.clv_beat_pct }}%</b></div>
        <div class="bar"><i :style="{ width: data.clv_beat_pct + '%' }" /></div>
        <div class="note">The number that matters. Beat the closing price and profit follows — even on weeks you lose bets. ({{ data.clv_sample }} graded)</div>
      </div>

      <!-- recent -->
      <div class="sect" v-if="data.recent.length">Recent</div>
      <div v-for="(h, i) in data.recent" :key="i" class="hi">
        <div class="mk" :class="h.result === 'win' ? 'w' : 'l'">{{ h.result === 'win' ? 'W' : h.result === 'loss' ? 'L' : 'P' }}</div>
        <div class="t">{{ h.pick }}<small>{{ h.league }}</small></div>
        <div class="p" :class="h.pnl_units >= 0 ? 'green' : 'red'">{{ money(h.pnl_units) }}</div>
      </div>

      <p v-if="data.settled === 0" class="pending">
        <template v-if="data.clv_beat_pct != null">Win/loss & ROI fill in as games finish — CLV is graded the moment the line closes.</template>
        <template v-else>No graded signals yet. Results appear here as picks settle.</template>
      </p>

      <p class="foot">Verified at a flat 1-unit stake · {{ unitNote }}. For entertainment — 1-800-GAMBLER.</p>
    </template>

    <p v-else class="pending">Loading…</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface Results {
  clv_beat_pct: number | null; clv_sample: number; settled: number
  wins: number; losses: number; pushes: number; win_rate: number | null
  pnl_units: number; roi_pct: number | null; curve: number[]
  recent: { pick: string; league: string; result: string; pnl_units: number }[]
}

const auth = useAuthStore()
const router = useRouter()
const data = ref<Results | null>(null)
const error = ref('')

// 1 unit = 1% of the user's stated bankroll.
const unitDollars = computed(() => auth.bankroll / 100)
const unitNote = computed(() => `1 unit = $${unitDollars.value.toFixed(0)} (1% of $${auth.bankroll.toLocaleString()})`)
function money(units: number) {
  const d = units * unitDollars.value
  return (d >= 0 ? '+$' : '−$') + Math.abs(d).toFixed(0)
}
const pnlUnits = computed(() => {
  const u = data.value?.pnl_units ?? 0
  return (u >= 0 ? '+' : '−') + Math.abs(u).toFixed(1) + 'u'
})
const pnlClass = computed(() => ((data.value?.pnl_units ?? 0) >= 0 ? 'green' : 'red'))
const heroSub = computed(() => {
  const d = data.value
  if (!d) return ''
  if (d.settled === 0) return `${d.clv_sample} graded · awaiting results`
  return `${money(d.pnl_units)} · ${d.settled} bets · ${unitNote.value}`
})

// curve scaling
const linePoints = computed(() => pts().map(p => `${p.x},${p.y}`).join(' '))
const areaPoints = computed(() => {
  const p = pts()
  return [...p.map(q => `${q.x},${q.y}`), '340,100', '0,100'].join(' ')
})
function pts() {
  const c = [0, ...(data.value?.curve ?? [])] // start at 0
  const min = Math.min(...c), max = Math.max(...c)
  const span = max - min || 1
  return c.map((v, i) => ({
    x: (i / (c.length - 1)) * 340,
    y: 92 - ((v - min) / span) * 84,
  }))
}

async function load() {
  try {
    const res = await auth.authFetch('/results')
    if (res.status === 401) { router.push('/login'); return }
    if (!res.ok) throw new Error('Failed to load results')
    data.value = await res.json()
  } catch (e: any) { error.value = e.message }
}

onMounted(() => {
  if (!auth.isAuthed) { router.push('/login'); return }
  load()
})
</script>

<style scoped>
.trk { max-width: 460px; margin: 0 auto; padding: 14px 14px 40px; color: #eef3f2; font-family: 'Archivo', sans-serif; }
.sect-title { font-size: 11px; color: #5f6f71; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 2px 0 4px; }
.topbar { display: flex; align-items: center; gap: 9px; padding: 8px 0 14px; border-bottom: 1px solid #222d30; }
.head { font-family: 'Archivo Narrow', sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; font-size: 15px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #1fd65f; box-shadow: 0 0 10px #1fd65f; }
.badge { margin-left: auto; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; padding: 4px 10px; border-radius: 20px; }
.badge.free { background: #1a2123; color: #8a9a9c; } .badge.pro { background: #ffc94d; color: #241a00; }
.err { color: #ff5a52; padding: 10px 0; }
.hero { text-align: center; padding: 18px 0 6px; }
.hero .big { font-family: 'Spline Sans Mono', monospace; font-weight: 600; font-size: 40px; line-height: 1; }
.green { color: #1fd65f; } .red { color: #ff5a52; }
.hero .sub { color: #8a9a9c; font-size: 12px; margin-top: 8px; }
.curve { width: 100%; height: 100px; margin: 6px 0; }
.row3 { display: flex; gap: 9px; margin: 12px 0; }
.box { flex: 1; background: #13191b; border: 1px solid #222d30; border-radius: 11px; padding: 11px 8px; text-align: center; }
.box .v { font-family: 'Spline Sans Mono', monospace; font-weight: 600; font-size: 18px; }
.box .l { font-size: 9px; color: #5f6f71; text-transform: uppercase; letter-spacing: .4px; margin-top: 3px; }
.clv { background: #13191b; border: 1px solid #222d30; border-radius: 11px; padding: 13px; margin-bottom: 14px; }
.clv .h { font-size: 12px; font-weight: 700; display: flex; justify-content: space-between; }
.clv .h b { color: #1fd65f; font-family: 'Spline Sans Mono', monospace; }
.clv .bar { height: 8px; border-radius: 5px; background: #222d30; margin-top: 9px; overflow: hidden; }
.clv .bar i { display: block; height: 100%; background: #1fd65f; border-radius: 5px; }
.clv .note { font-size: 11px; color: #8a9a9c; margin-top: 8px; line-height: 1.45; }
.sect { font-size: 11px; color: #5f6f71; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 6px 0 4px; }
.hi { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-top: 1px solid #222d30; }
.mk { width: 21px; height: 21px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 800; }
.mk.w { background: #0e3f23; color: #1fd65f; } .mk.l { background: #3d1411; color: #ff5a52; }
.hi .t { flex: 1; font-size: 12px; font-weight: 600; } .hi .t small { display: block; color: #5f6f71; font-weight: 500; font-size: 10.5px; margin-top: 1px; }
.hi .p { font-family: 'Spline Sans Mono', monospace; font-weight: 600; font-size: 13px; }
.pending { color: #8a9a9c; font-size: 12.5px; padding: 16px 2px; line-height: 1.5; text-align: center; }
.foot { text-align: center; color: #5f6f71; font-size: 10.5px; margin-top: 18px; line-height: 1.5; }
</style>
