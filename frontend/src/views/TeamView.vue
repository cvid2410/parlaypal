<template>
  <div class="tv">
    <a class="back" @click="router.back()">← {{ $t('common.back') }}</a>
    <p v-if="error" class="err">{{ error }}</p>

    <template v-else-if="data">
      <div class="thead">
        <img v-if="data.team.logo" :src="data.team.logo" class="tcrest" alt="" />
        <h2>{{ data.team.name || $t('team.fallback') }}</h2>
      </div>

      <div class="sect">{{ $t('common.upcoming') }}</div>
      <p v-if="!data.upcoming.length" class="empty">{{ $t('team.no_upcoming') }}</p>
      <div v-else class="glist">
        <div v-for="(g, i) in data.upcoming" :key="'u' + i" class="grow">
          <span class="ha" :class="g.home_away === 'H' ? 'h' : 'a'">{{ g.home_away }}</span>
          <span class="opp"><img v-if="g.opponent_logo" :src="g.opponent_logo" class="crest" loading="lazy" alt="" />{{ g.opponent }}</span>
          <span class="lg">{{ g.league }}</span>
          <span class="ko">{{ ko(g.kickoff) }}</span>
        </div>
      </div>
      <button v-if="data.upcoming.length >= next" class="more" :disabled="busy" @click="moreUpcoming">{{ $t('team.more_upcoming') }}</button>

      <div class="sect">{{ $t('team.previous') }}</div>
      <p v-if="!data.past.length" class="empty">{{ $t('team.no_past') }}</p>
      <div v-else class="glist">
        <div v-for="(g, i) in data.past" :key="'p' + i" class="grow">
          <span class="ha" :class="g.home_away === 'H' ? 'h' : 'a'">{{ g.home_away }}</span>
          <span class="opp"><img v-if="g.opponent_logo" :src="g.opponent_logo" class="crest" loading="lazy" alt="" />{{ g.opponent }}</span>
          <span class="lg">{{ g.league }}</span>
          <span class="res" :class="result(g)">{{ result(g).toUpperCase() }}</span>
          <span class="score">{{ scoreText(g) }}</span>
        </div>
      </div>
      <button v-if="data.past.length >= last" class="more" :disabled="busy" @click="morePast">{{ $t('team.more_past') }}</button>
    </template>

    <div v-else aria-hidden="true">
      <div class="sk" style="width: 220px; height: 26px; margin: 16px 0 20px" />
      <div v-for="n in 6" :key="n" class="skrow"><div class="sk" style="width: 60%; height: 14px" /></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { dateLong, kickoffLong } from '../lib/datetime'

interface Game { opponent: string; opponent_logo: string | null; home_away: string; league: string; kickoff: string; status: string; minute: number | null; team_score: number | null; opp_score: number | null }
interface TeamData { team: { name: string | null; logo: string | null }; past: Game[]; upcoming: Game[] }

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const data = ref<TeamData | null>(null)
const error = ref('')
const busy = ref(false)
const last = ref(10)
const next = ref(10)

function ko(iso: string) {
  return kickoffLong(iso)
}
function result(g: Game) {
  if (g.team_score == null || g.opp_score == null) return ''
  if (g.team_score > g.opp_score) return 'win'
  if (g.team_score < g.opp_score) return 'loss'
  return 'draw'
}
function scoreText(g: Game) {
  if (g.team_score == null || g.opp_score == null) return dateLong(g.kickoff)
  return `${g.team_score}-${g.opp_score}`
}

async function load() {
  busy.value = true
  try {
    const res = await auth.authFetch(`/teams/${route.params.id}?last=${last.value}&next=${next.value}`)
    if (res.status === 401) { router.push('/login'); return }
    if (!res.ok) throw new Error(t('team.load_error'))
    data.value = await res.json()
  } catch (e: any) { error.value = e.message } finally { busy.value = false }
}

function morePast() { last.value += 10; load() }
function moreUpcoming() { next.value += 10; load() }

// Reset + reload when navigating between teams without unmounting.
watch(() => route.params.id, () => { last.value = 10; next.value = 10; data.value = null; load() })

onMounted(() => {
  if (!auth.isAuthed) { router.push('/login'); return }
  load()
})
</script>

<style scoped>
.tv { color: var(--txt); max-width: 760px; }
.back { font-size: 13px; color: var(--txt-2); font-weight: 600; cursor: pointer; }
.back:hover { color: var(--txt); }
.thead { display: flex; align-items: center; gap: 14px; margin: 16px 0 20px; }
.thead .tcrest { width: 40px; height: 40px; object-fit: contain; }
.thead h2 { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 26px; font-weight: 700; letter-spacing: -.02em; }
.sect { font-size: 11px; color: var(--txt-3); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 18px 0 12px; }
.glist { display: flex; flex-direction: column; gap: 8px; }
.grow { display: grid; grid-template-columns: 26px 1fr auto auto; align-items: center; gap: 12px; padding: 12px 16px; border: 1px solid var(--hair); border-radius: 12px; background: var(--panel); }
.ha { font-family: 'Spline Sans Mono', monospace; font-size: 11px; font-weight: 700; width: 22px; height: 22px; display: grid; place-items: center; border-radius: 6px; }
.ha.h { color: var(--green); background: color-mix(in srgb, var(--green) 14%, transparent); }
.ha.a { color: var(--txt-3); background: var(--surface-2); }
.opp { display: flex; align-items: center; gap: 9px; font-size: 14.5px; font-weight: 500; min-width: 0; }
.opp .crest { width: 19px; height: 19px; object-fit: contain; flex-shrink: 0; }
.lg { font-size: 11.5px; color: var(--txt-3); white-space: nowrap; }
.ko { font-size: 11.5px; color: var(--txt-3); white-space: nowrap; }
.res { font-family: 'Spline Sans Mono', monospace; font-size: 11px; font-weight: 700; }
.res.win { color: var(--green); }
.res.loss { color: #ff5a52; }
.res.draw { color: var(--txt-3); }
.score { font-family: 'Spline Sans Mono', monospace; font-size: 15px; font-weight: 600; min-width: 38px; text-align: right; }
.more { margin: 12px 0 4px; padding: 9px 16px; font-size: 12.5px; font-weight: 600; color: var(--txt-2); background: var(--panel); border: 1px solid var(--hair); border-radius: 10px; cursor: pointer; }
.more:hover:not(:disabled) { color: var(--txt); border-color: var(--hair-2); }
.more:disabled { opacity: .5; cursor: default; }
.err { color: #ff5a52; padding: 8px 0; }
.empty { color: var(--txt-2); font-size: 13.5px; padding: 4px 0 8px; }
.skrow { padding: 12px 16px; border: 1px solid var(--hair); border-radius: 12px; margin-bottom: 8px; }

@media (max-width: 620px) {
  .grow { grid-template-columns: 24px 1fr auto; }
  .lg { display: none; }
}
</style>
