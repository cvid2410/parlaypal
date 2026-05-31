<template>
  <div class="scr">
    <p v-if="error" class="err">{{ error }}</p>

    <template v-else-if="data">
      <div v-if="data.live.length" class="sect"><span class="live" /> Live now</div>
      <div v-for="(m, i) in data.live" :key="'l' + i" class="match">
        <div class="lg">{{ m.league }} · {{ m.country }} <span class="min">{{ m.minute ? m.minute + "'" : 'LIVE' }}</span></div>
        <Row :m="m" />
      </div>

      <div v-if="data.upcoming.length" class="sect">Today · upcoming</div>
      <div v-for="(m, i) in data.upcoming" :key="'u' + i" class="match">
        <div class="lg">{{ m.league }} · {{ m.country }} <span class="min ft">{{ time(m.kickoff) }}</span></div>
        <Row :m="m" />
      </div>

      <div v-if="data.finished.length" class="sect">Finished today</div>
      <div v-for="(m, i) in data.finished" :key="'f' + i" class="match">
        <div class="lg">{{ m.league }} · {{ m.country }} <span class="min ft">FT</span></div>
        <Row :m="m" />
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

// Inline score row (avoids a separate file for one tiny component).
const Row = (props: { m: M }) => {
  const { m } = props
  const score = (s: number | null) => (s == null ? '–' : String(s))
  const win = (a: number | null, b: number | null) => a != null && b != null && a > b
  return h('div', {}, [
    h('div', { class: ['team', win(m.home_score, m.away_score) ? 'w' : ''] }, [
      h('span', { class: 'nm' }, m.home), h('span', { class: 'sc' }, score(m.home_score)),
    ]),
    h('div', { class: ['team', win(m.away_score, m.home_score) ? 'w' : ''] }, [
      h('span', { class: 'nm' }, m.away), h('span', { class: 'sc' }, score(m.away_score)),
    ]),
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
.scr { max-width: 460px; margin: 0 auto; padding: 14px 12px 30px; color: #eef3f2; font-family: 'Archivo', sans-serif; }
.sect { font-size: 11px; color: #5f6f71; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 16px 4px 10px; display: flex; align-items: center; gap: 7px; }
.sect .live { width: 7px; height: 7px; border-radius: 50%; background: #ff5a52; }
.match { background: #13191b; border: 1px solid #222d30; border-radius: 13px; padding: 12px 13px; margin-bottom: 9px; }
.lg { font-size: 10px; color: #5f6f71; text-transform: uppercase; letter-spacing: .6px; margin-bottom: 8px; display: flex; justify-content: space-between; }
.lg .min { color: #ff5a52; font-family: 'Spline Sans Mono', monospace; font-weight: 600; }
.lg .min.ft { color: #5f6f71; }
:deep(.team) { display: flex; align-items: center; gap: 9px; padding: 3px 0; }
:deep(.team .nm) { font-size: 14px; font-weight: 600; flex: 1; }
:deep(.team .sc) { font-family: 'Spline Sans Mono', monospace; font-weight: 600; font-size: 16px; }
:deep(.team.w .nm) { font-weight: 700; }
.err { color: #ff5a52; padding: 10px 4px; }
.empty { color: #8a9a9c; font-size: 13px; padding: 16px 4px; }
</style>
