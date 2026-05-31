<template>
  <div class="scr">
    <p v-if="error" class="err">{{ error }}</p>

    <template v-else-if="data">
      <div class="cols">
        <div class="panel">
          <div class="ph"><span class="d" /> Live now</div>
          <div v-if="!data.live.length" class="pe">No live matches in your leagues.</div>
          <Match v-for="(m, i) in data.live" :key="'l' + i" :m="m" :label="m.minute ? m.minute + `'` : 'LIVE'" />
        </div>
        <div class="panel">
          <div class="ph">Today · upcoming</div>
          <div v-if="!data.upcoming.length" class="pe">Nothing left to kick off today.</div>
          <Match v-for="(m, i) in data.upcoming" :key="'u' + i" :m="m" :label="time(m.kickoff)" />
        </div>
      </div>

      <div v-if="data.finished.length" class="panel wide">
        <div class="ph">Finished today</div>
        <Match v-for="(m, i) in data.finished" :key="'f' + i" :m="m" label="FT" />
      </div>

      <p v-if="!data.live.length && !data.upcoming.length && !data.finished.length" class="empty">
        No fixtures in your leagues today.
      </p>
    </template>
    <p v-else class="empty">Loading scores…</p>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface M { league: string; country: string; home: string; away: string; home_score: number | null; away_score: number | null; status: string; minute: number | null; kickoff: string }
interface Scores { live: M[]; upcoming: M[]; finished: M[] }

const auth = useAuthStore()
const router = useRouter()
const data = ref<Scores | null>(null)
const error = ref('')

function time(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

const Match = (props: { m: M; label: string }) => {
  const { m, label } = props
  const sc = (s: number | null) => (s == null ? '—' : String(s))
  const w = (a: number | null, b: number | null) => a != null && b != null && a > b
  const team = (name: string, score: number | null, win: boolean) =>
    h('div', { class: ['trow', win ? 'w' : ''] }, [
      h('span', { class: 'dt' }), h('span', { class: 'n' }, name), h('span', { class: 'sc' }, sc(score)),
    ])
  return h('div', { class: 'match' }, [
    h('div', { class: 'meta' }, [h('span', `${m.league} · ${m.country}`), h('span', { class: 'm' }, label)]),
    team(m.home, m.home_score, w(m.home_score, m.away_score)),
    team(m.away, m.away_score, w(m.away_score, m.home_score)),
  ])
}

async function load() {
  try {
    const res = await auth.authFetch('/scores')
    if (res.status === 401) { router.push('/login'); return }
    if (!res.ok) throw new Error('Failed to load scores')
    data.value = await res.json()
  } catch (e: any) { error.value = e.message }
}

onMounted(() => {
  if (!auth.isAuthed) { router.push('/login'); return }
  load()
})
</script>

<style scoped>
.scr { color: var(--txt); }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
.panel { border: 1px solid var(--hair); border-radius: 16px; overflow: hidden; background: var(--panel); }
.panel.wide { margin-top: 16px; max-width: 560px; }
.ph { padding: 14px 18px; border-bottom: 1px solid var(--hair); font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--txt-3); display: flex; align-items: center; gap: 9px; }
.ph .d { width: 6px; height: 6px; border-radius: 50%; background: var(--green); }
.pe { padding: 18px; color: var(--txt-3); font-size: 13px; }
:deep(.match) { padding: 15px 18px; }
:deep(.match + .match) { border-top: 1px solid var(--hair); }
:deep(.match .meta) { display: flex; justify-content: space-between; font-size: 11.5px; color: var(--txt-3); margin-bottom: 11px; font-weight: 500; }
:deep(.match .meta .m) { font-family: 'Spline Sans Mono', monospace; color: var(--green); }
:deep(.trow) { display: flex; align-items: center; gap: 11px; padding: 4px 0; }
:deep(.trow .dt) { width: 6px; height: 6px; border-radius: 50%; background: var(--txt-3); }
:deep(.trow.w .dt) { background: var(--green); }
:deep(.trow .n) { flex: 1; font-size: 14.5px; }
:deep(.trow.w .n) { font-weight: 700; }
:deep(.trow .sc) { font-family: 'Spline Sans Mono', monospace; font-size: 16px; color: var(--txt-3); font-weight: 600; }
:deep(.trow.w .sc) { color: var(--txt); }
.err { color: #ff5a52; padding: 8px 0; }
.empty { color: var(--txt-2); font-size: 13.5px; padding: 16px 0; }

@media (max-width: 900px) { .cols { grid-template-columns: 1fr; } }
</style>
