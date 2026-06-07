<template>
  <div class="scr">
    <p v-if="error" class="err">{{ error }}</p>

    <template v-else-if="data">
      <p v-if="allEmpty" class="empty">{{ $t('scores.empty') }}</p>
      <div v-else class="cols">
        <!-- left: what's happening / happened -->
        <div class="col">
          <div class="panel">
            <div class="ph"><span class="d" aria-hidden="true" /> {{ $t('scores.live_now') }}</div>
            <div v-if="!data.live.length" class="pe">{{ $t('scores.no_live') }}</div>
            <Match v-for="(m, i) in data.live" :key="'l' + i" :m="m" :label="m.minute ? m.minute + `'` : $t('scores.live_label')" />
          </div>
          <div v-if="data.finished.length" class="panel">
            <div class="ph">{{ $t('scores.finished_today') }}</div>
            <Match v-for="(m, i) in data.finished" :key="'f' + i" :m="m" label="FT" />
          </div>
        </div>

        <!-- right: what's next / off -->
        <div class="col">
          <div class="panel">
            <div class="ph">{{ $t('scores.today_upcoming') }}</div>
            <div v-if="!data.upcoming.length" class="pe">{{ $t('scores.nothing_upcoming') }}</div>
            <Match v-for="(m, i) in data.upcoming" :key="'u' + i" :m="m" :label="time(m.kickoff)" />
          </div>
          <div v-if="data.off && data.off.length" class="panel off">
            <div class="ph">{{ $t('scores.cancelled') }}</div>
            <Match v-for="(m, i) in data.off" :key="'o' + i" :m="m" :label="(m.note || $t('scores.off_label')).toUpperCase()" />
          </div>
        </div>
      </div>
    </template>
    <div v-else class="cols" aria-hidden="true">
      <div v-for="c in 2" :key="c" class="panel">
        <div class="ph"><span class="sk" style="width: 90px; height: 12px" /></div>
        <div v-for="n in 3" :key="n" class="skrow">
          <div class="sk" style="width: 55%; height: 12px; margin-bottom: 12px" />
          <div class="sk" style="width: 80%; height: 15px; margin: 8px 0" />
          <div class="sk" style="width: 70%; height: 15px" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { timeShort } from '../lib/datetime'

interface M { league_id: number; league: string; country: string; home: string; away: string; home_logo: string | null; away_logo: string | null; home_score: number | null; away_score: number | null; status: string; note: string | null; minute: number | null; kickoff: string; venue: string | null; venue_city: string | null }
interface Scores { live: M[]; upcoming: M[]; finished: M[]; off: M[] }

const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()
const data = ref<Scores | null>(null)
const error = ref('')

const allEmpty = computed(() => {
  const d = data.value
  return !!d && !d.live.length && !d.upcoming.length && !d.finished.length && !(d.off && d.off.length)
})

function time(iso: string) {
  return timeShort(iso)
}

const Match = (props: { m: M; label: string }) => {
  const { m, label } = props
  const sc = (s: number | null) => (s == null ? '-' : String(s))
  const w = (a: number | null, b: number | null) => a != null && b != null && a > b
  const crest = (logo: string | null) =>
    logo
      ? h('img', { class: 'crest', src: logo, loading: 'lazy', alt: '' })
      : h('span', { class: 'dt', 'aria-hidden': 'true' })
  const team = (name: string, score: number | null, win: boolean, logo: string | null) =>
    h('div', { class: ['trow', win ? 'w' : ''] }, [
      crest(logo), h('span', { class: 'n' }, name), h('span', { class: 'sc' }, sc(score)),
    ])
  return h('div', { class: 'match', onClick: () => router.push(`/leagues/${m.league_id}`), title: `Open ${m.league}` }, [
    h('div', { class: 'meta' }, [
      h('span', `${m.league} · ${m.country}`),
      h('span', { class: ['m', m.status === 'live' ? 'live' : ''] }, label),
    ]),
    team(m.home, m.home_score, w(m.home_score, m.away_score), m.home_logo),
    team(m.away, m.away_score, w(m.away_score, m.home_score), m.away_logo),
    m.venue
      ? h('div', { class: 'venue' }, `\u{1F4CD} ${m.venue}${m.venue_city ? ' · ' + m.venue_city : ''}`)
      : null,
  ])
}

async function load() {
  try {
    // Send the browser's timezone so "today" is the user's local day, not UTC.
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
    const res = await auth.authFetch(`/scores?tz=${encodeURIComponent(tz)}`)
    if (res.status === 401) { router.push('/login'); return }
    if (!res.ok) throw new Error(t('scores.load_error'))
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
.col { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.panel { border: 1px solid var(--hair); border-radius: 16px; overflow: hidden; background: var(--panel); }
.panel.off { opacity: .62; }
.panel.off :deep(.match .meta .m) { color: var(--txt-3); }
.ph { padding: 14px 18px; border-bottom: 1px solid var(--hair); font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--txt-3); display: flex; align-items: center; gap: 9px; }
.ph .d { width: 6px; height: 6px; border-radius: 50%; background: var(--green); }
.pe { padding: 18px; color: var(--txt-3); font-size: 13px; }
:deep(.match) { padding: 15px 18px; cursor: pointer; transition: background .15s; }
:deep(.match:hover) { background: var(--surface-2); }
:deep(.match + .match) { border-top: 1px solid var(--hair); }
:deep(.match .meta) { display: flex; justify-content: space-between; font-size: 11.5px; color: var(--txt-3); margin-bottom: 11px; font-weight: 500; }
:deep(.match .meta .m) { font-family: 'Spline Sans Mono', monospace; color: var(--green); }
:deep(.match .meta .m.live) { color: #fff; background: #e0245e; padding: 2px 9px; border-radius: 100px; font-size: 10.5px; font-weight: 700; display: inline-flex; align-items: center; gap: 5px; }
:deep(.match .meta .m.live)::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #fff; animation: livepulse 1.2s infinite; }
@keyframes livepulse { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
:deep(.match .venue) { font-size: 11px; color: var(--txt-3); margin-top: 9px; }
:deep(.trow) { display: flex; align-items: center; gap: 11px; padding: 4px 0; }
:deep(.trow .dt) { width: 18px; height: 18px; border-radius: 50%; background: var(--surface-2); display: inline-block; }
:deep(.trow .crest) { width: 18px; height: 18px; object-fit: contain; }
:deep(.trow .n) { flex: 1; font-size: 14.5px; }
:deep(.trow.w .n) { font-weight: 700; }
:deep(.trow .sc) { font-family: 'Spline Sans Mono', monospace; font-size: 16px; color: var(--txt-3); font-weight: 600; }
:deep(.trow.w .sc) { color: var(--txt); }
.err { color: #ff5a52; padding: 8px 0; }
.empty { color: var(--txt-2); font-size: 13.5px; padding: 16px 0; }
.skrow { padding: 15px 18px; }
.skrow + .skrow { border-top: 1px solid var(--hair); }

@media (max-width: 900px) { .cols { grid-template-columns: 1fr; } }
</style>
