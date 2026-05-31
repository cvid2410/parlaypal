<template>
  <div class="ln">
    <a class="back" @click="$router.back()">← Back</a>
    <p v-if="error" class="err">{{ error }}</p>

    <template v-else-if="data">
      <div class="head">
        <div class="teams">
          <img v-if="data.home_logo" :src="data.home_logo" class="crest" />
          <span>{{ data.home }}</span><span class="vs">vs</span><span>{{ data.away }}</span>
          <img v-if="data.away_logo" :src="data.away_logo" class="crest" />
        </div>
        <div class="meta">{{ data.league }} · {{ data.country }} · {{ kickoff(data.kickoff) }}</div>
      </div>

      <p v-if="data.markets.length === 0" class="empty">No live prices for this fixture right now.</p>

      <div v-for="m in data.markets" :key="m.market_id" class="market">
        <div class="mh">{{ marketName(m) }}</div>
        <div v-for="s in m.selections" :key="s.selection" class="sel">
          <div class="sl">{{ s.label }}</div>
          <div class="best"><b>{{ s.best_odds }}</b><small>{{ s.best_book }}</small></div>
          <div class="all">
            <span v-for="(b, i) in s.books" :key="i" class="bk" :class="{ top: i === 0 }">
              {{ b.book }} <em>{{ b.odds }}</em>
            </span>
          </div>
        </div>
      </div>
      <p class="foot">Best available price across the books we track · for entertainment · 1-800-GAMBLER.</p>
    </template>
    <p v-else class="empty">Loading prices…</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface Book { book: string; odds: string }
interface Sel { selection: string; label: string; best_book: string; best_odds: string; books: Book[] }
interface M { market_id: number; type: string; line: number | null; selections: Sel[] }
interface Board { league: string; country: string; home: string; away: string; home_logo: string | null; away_logo: string | null; kickoff: string; markets: M[] }

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const data = ref<Board | null>(null)
const error = ref('')

function kickoff(iso: string) {
  return new Date(iso).toLocaleString([], { weekday: 'short', hour: 'numeric', minute: '2-digit' })
}
function marketName(m: M) {
  if (m.type === 'h2h') return 'Match result'
  if (m.type === 'total') return `Total goals · ${m.line}`
  return m.type
}

async function load() {
  try {
    const res = await auth.authFetch(`/lines/${route.params.id}`)
    if (res.status === 401) { router.push('/login'); return }
    if (!res.ok) throw new Error('Failed to load prices')
    data.value = await res.json()
  } catch (e: any) { error.value = e.message }
}

onMounted(() => {
  if (!auth.isAuthed) { router.push('/login'); return }
  load()
})
</script>

<style scoped>
.ln { color: var(--txt); max-width: 760px; }
.back { font-size: 13px; color: var(--txt-2); font-weight: 600; cursor: pointer; }
.back:hover { color: var(--txt); }
.head { margin: 16px 0 20px; }
.teams { display: flex; align-items: center; gap: 10px; font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 24px; font-weight: 700; letter-spacing: -.02em; }
.teams .vs { color: var(--txt-3); font-size: 15px; font-weight: 500; }
.teams .crest { width: 26px; height: 26px; object-fit: contain; }
.head .meta { font-size: 12.5px; color: var(--txt-3); margin-top: 8px; }
.market { border: 1px solid var(--hair); border-radius: 14px; background: var(--panel); margin-bottom: 14px; overflow: hidden; }
.mh { padding: 13px 18px; border-bottom: 1px solid var(--hair); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--txt-3); }
.sel { padding: 14px 18px; display: grid; grid-template-columns: 1fr auto; gap: 8px 14px; align-items: center; }
.sel + .sel { border-top: 1px solid var(--hair); }
.sl { font-size: 14.5px; font-weight: 600; }
.best { text-align: right; }
.best b { font-family: 'Spline Sans Mono', monospace; font-size: 18px; color: var(--green); }
.best small { display: block; font-size: 10.5px; color: var(--txt-3); margin-top: 2px; }
.all { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 7px; }
.bk { font-size: 11px; color: var(--txt-3); border: 1px solid var(--hair); border-radius: 100px; padding: 3px 9px; }
.bk em { font-family: 'Spline Sans Mono', monospace; font-style: normal; color: var(--txt-2); }
.bk.top { border-color: var(--green-dim); color: var(--green); }
.bk.top em { color: var(--green); }
.err { color: #ff5a52; padding: 8px 0; }
.empty { color: var(--txt-2); font-size: 13.5px; padding: 16px 0; }
.foot { color: var(--txt-3); font-size: 11px; margin-top: 18px; }
</style>
