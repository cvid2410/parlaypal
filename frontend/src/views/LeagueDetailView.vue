<template>
  <div class="ld">
    <RouterLink to="/leagues" class="back">← {{ $t('common.all_leagues') }}</RouterLink>
    <p v-if="error" class="err">{{ error }}</p>

    <template v-else-if="data">
      <div class="lhead">
        <h2>{{ data.league }}</h2>
        <span class="meta">{{ data.country }}<template v-if="data.season"> · {{ data.season }}</template></span>
      </div>

      <template v-if="fixtures.length">
        <div class="sect">{{ $t('common.upcoming') }}</div>
        <div class="fxlist">
          <div v-for="(fx, i) in fixtures" :key="i" class="fxrow">
            <span class="t">
              <RouterLink v-if="fx.home_af_id" :to="`/teams/${fx.home_af_id}`" class="tlink"><img v-if="fx.home_logo" :src="fx.home_logo" class="crest" alt="" />{{ fx.home }}</RouterLink>
              <template v-else><img v-if="fx.home_logo" :src="fx.home_logo" class="crest" alt="" />{{ fx.home }}</template>
            </span>
            <span class="vs">v</span>
            <span class="t r">
              <RouterLink v-if="fx.away_af_id" :to="`/teams/${fx.away_af_id}`" class="tlink"><img v-if="fx.away_logo" :src="fx.away_logo" class="crest" alt="" />{{ fx.away }}</RouterLink>
              <template v-else><img v-if="fx.away_logo" :src="fx.away_logo" class="crest" alt="" />{{ fx.away }}</template>
            </span>
            <span class="ko">{{ ko(fx.kickoff) }}</span>
            <RouterLink v-if="fx.fixture_id" :to="`/lines/${fx.fixture_id}`" class="odds">{{ $t('ld.odds') }}</RouterLink>
            <span v-else class="odds dis">-</span>
          </div>
        </div>
      </template>

      <div v-if="data.available || data.groups.length" class="sect">{{ $t('ld.table') }}</div>
      <p v-if="!data.available" class="empty">{{ $t('ld.no_standings') }}</p>

      <div v-for="(g, gi) in data.groups" :key="gi" class="table">
        <div v-if="g.group && data.groups.length > 1" class="gname">{{ g.group }}</div>
        <div class="thead">
          <span class="r">#</span><span class="t">{{ $t('ld.team_col') }}</span>
          <span class="n">{{ $t('ld.col_p') }}</span><span class="n hide-s">{{ $t('ld.col_w') }}</span><span class="n hide-s">{{ $t('ld.col_d') }}</span><span class="n hide-s">{{ $t('ld.col_l') }}</span>
          <span class="n">{{ $t('ld.col_gd') }}</span><span class="n pts">{{ $t('ld.col_pts') }}</span>
        </div>
        <div v-for="row in g.rows" :key="row.rank" class="trow" :class="{ top: row.rank <= 4 }">
          <span class="r">{{ row.rank }}</span>
          <span class="t">
            <RouterLink v-if="row.af_team_id" :to="`/teams/${row.af_team_id}`" class="tlink">
              <img v-if="row.logo" :src="row.logo" class="crest" loading="lazy" alt="" />{{ row.team }}
            </RouterLink>
            <template v-else><img v-if="row.logo" :src="row.logo" class="crest" loading="lazy" alt="" />{{ row.team }}</template>
          </span>
          <span class="n">{{ row.played }}</span>
          <span class="n hide-s">{{ row.win }}</span><span class="n hide-s">{{ row.draw }}</span><span class="n hide-s">{{ row.lose }}</span>
          <span class="n">{{ row.gd > 0 ? '+' + row.gd : row.gd }}</span>
          <span class="n pts">{{ row.points }}</span>
        </div>
      </div>
    </template>
    <div v-else aria-hidden="true">
      <div class="sk" style="width: 220px; height: 26px; margin: 16px 0 20px" />
      <div class="table">
        <div v-for="n in 8" :key="n" class="skrow">
          <div class="sk" style="width: 16px; height: 13px" />
          <div class="sk" style="width: 40%; height: 14px" />
          <div class="sk" style="width: 28px; height: 13px; margin-left: auto" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface Row { rank: number; team: string; af_team_id: number | null; logo: string | null; points: number; played: number; win: number; draw: number; lose: number; gd: number; form: string | null }
interface Standings { league: string; country: string; available: boolean; season?: number; groups: { group: string; rows: Row[] }[] }

interface Fx { home: string; home_logo: string | null; home_af_id: number | null; away: string; away_logo: string | null; away_af_id: number | null; kickoff: string; status: string; fixture_id: string | null }

const auth = useAuthStore()
const route = useRoute()
const { t } = useI18n()
const router = useRouter()
const data = ref<Standings | null>(null)
const fixtures = ref<Fx[]>([])
const error = ref('')

function ko(iso: string) {
  return new Date(iso).toLocaleString([], { weekday: 'short', hour: 'numeric', minute: '2-digit' })
}

async function load() {
  try {
    const [st, fx] = await Promise.all([
      auth.authFetch(`/standings/${route.params.id}`),
      auth.authFetch(`/leagues/${route.params.id}/schedule`),
    ])
    if (st.status === 401) { router.push('/login'); return }
    if (!st.ok) throw new Error(t('ld.load_error'))
    data.value = await st.json()
    if (fx.ok) fixtures.value = (await fx.json()).fixtures
  } catch (e: any) { error.value = e.message }
}

onMounted(() => {
  if (!auth.isAuthed) { router.push('/login'); return }
  load()
})
</script>

<style scoped>
.ld { color: var(--txt); max-width: 760px; }
.back { font-size: 13px; color: var(--txt-2); font-weight: 600; }
.back:hover { color: var(--txt); }
.lhead { display: flex; align-items: baseline; gap: 12px; margin: 16px 0 18px; }
.lhead h2 { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 26px; font-weight: 700; letter-spacing: -.02em; }
.lhead .meta { font-size: 13px; color: var(--txt-3); }
.sect { font-size: 11px; color: var(--txt-3); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 4px 0 12px; }
.fxlist { display: flex; flex-direction: column; gap: 8px; margin-bottom: 24px; }
.fxrow { display: flex; align-items: center; gap: 10px; padding: 13px 16px; border: 1px solid var(--hair); border-radius: 12px; background: var(--panel); color: var(--txt); }
.fxrow .t { flex: 1; display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 500; min-width: 0; }
.fxrow .t.r { justify-content: flex-end; }
.fxrow .t .tlink { display: flex; align-items: center; gap: 8px; min-width: 0; color: var(--txt); }
.fxrow .t .tlink:hover { color: var(--green); }
.fxrow .crest { width: 19px; height: 19px; object-fit: contain; flex-shrink: 0; }
.fxrow .vs { color: var(--txt-3); font-size: 12px; }
.fxrow .ko { font-size: 11.5px; color: var(--txt-3); white-space: nowrap; }
.fxrow .odds { font-size: 11.5px; font-weight: 700; color: var(--green); white-space: nowrap; }
.fxrow .odds.dis { color: var(--txt-3); font-weight: 400; opacity: .55; }
.table { border: 1px solid var(--hair); border-radius: 14px; overflow: hidden; background: var(--panel); margin-bottom: 16px; }
.gname { padding: 12px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--txt-2); border-bottom: 1px solid var(--hair); }
.thead, .trow { display: grid; grid-template-columns: 28px 1fr 30px 30px 30px 30px 40px 44px; align-items: center; gap: 4px; padding: 11px 16px; }
.thead { font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; color: var(--txt-3); font-weight: 700; border-bottom: 1px solid var(--hair); }
.trow { font-size: 14px; }
.trow + .trow { border-top: 1px solid var(--hair); }
.trow.top .r { color: var(--green); font-weight: 700; }
.r { font-family: 'Spline Sans Mono', monospace; color: var(--txt-3); font-size: 12.5px; }
.t { display: flex; align-items: center; gap: 10px; font-weight: 500; min-width: 0; }
.t .tlink { display: flex; align-items: center; gap: 10px; min-width: 0; color: var(--txt); }
.t .tlink:hover { color: var(--green); }
.t .crest { width: 20px; height: 20px; object-fit: contain; flex-shrink: 0; }
.n { font-family: 'Spline Sans Mono', monospace; font-size: 13px; color: var(--txt-2); text-align: center; }
.n.pts { color: var(--txt); font-weight: 600; }
.err { color: #ff5a52; padding: 8px 0; }
.empty { color: var(--txt-2); font-size: 13.5px; padding: 16px 0; }
.skrow { display: flex; align-items: center; gap: 12px; padding: 12px 16px; }
.skrow + .skrow { border-top: 1px solid var(--hair); }

@media (max-width: 620px) {
  .thead, .trow { grid-template-columns: 24px 1fr 30px 40px 44px; }
  .hide-s { display: none; }
}
</style>
