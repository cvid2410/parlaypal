<template>
  <div class="ld">
    <RouterLink to="/leagues" class="back">← All leagues</RouterLink>
    <p v-if="error" class="err">{{ error }}</p>

    <template v-else-if="data">
      <div class="lhead">
        <h2>{{ data.league }}</h2>
        <span class="meta">{{ data.country }}<template v-if="data.season"> · {{ data.season }}</template></span>
      </div>

      <p v-if="!data.available" class="empty">Standings aren't available for this league yet.</p>

      <div v-for="(g, gi) in data.groups" :key="gi" class="table">
        <div v-if="g.group && data.groups.length > 1" class="gname">{{ g.group }}</div>
        <div class="thead">
          <span class="r">#</span><span class="t">Team</span>
          <span class="n">P</span><span class="n hide-s">W</span><span class="n hide-s">D</span><span class="n hide-s">L</span>
          <span class="n">GD</span><span class="n pts">Pts</span>
        </div>
        <div v-for="row in g.rows" :key="row.rank" class="trow" :class="{ top: row.rank <= 4 }">
          <span class="r">{{ row.rank }}</span>
          <span class="t"><img v-if="row.logo" :src="row.logo" class="crest" loading="lazy" />{{ row.team }}</span>
          <span class="n">{{ row.played }}</span>
          <span class="n hide-s">{{ row.win }}</span><span class="n hide-s">{{ row.draw }}</span><span class="n hide-s">{{ row.lose }}</span>
          <span class="n">{{ row.gd > 0 ? '+' + row.gd : row.gd }}</span>
          <span class="n pts">{{ row.points }}</span>
        </div>
      </div>
    </template>
    <p v-else class="empty">Loading table…</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface Row { rank: number; team: string; logo: string | null; points: number; played: number; win: number; draw: number; lose: number; gd: number; form: string | null }
interface Standings { league: string; country: string; available: boolean; season?: number; groups: { group: string; rows: Row[] }[] }

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const data = ref<Standings | null>(null)
const error = ref('')

async function load() {
  try {
    const res = await auth.authFetch(`/standings/${route.params.id}`)
    if (res.status === 401) { router.push('/login'); return }
    if (!res.ok) throw new Error('Failed to load standings')
    data.value = await res.json()
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
.table { border: 1px solid var(--hair); border-radius: 14px; overflow: hidden; background: var(--panel); margin-bottom: 16px; }
.gname { padding: 12px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--txt-2); border-bottom: 1px solid var(--hair); }
.thead, .trow { display: grid; grid-template-columns: 28px 1fr 30px 30px 30px 30px 40px 44px; align-items: center; gap: 4px; padding: 11px 16px; }
.thead { font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; color: var(--txt-3); font-weight: 700; border-bottom: 1px solid var(--hair); }
.trow { font-size: 14px; }
.trow + .trow { border-top: 1px solid var(--hair); }
.trow.top .r { color: var(--green); font-weight: 700; }
.r { font-family: 'Spline Sans Mono', monospace; color: var(--txt-3); font-size: 12.5px; }
.t { display: flex; align-items: center; gap: 10px; font-weight: 500; min-width: 0; }
.t .crest { width: 20px; height: 20px; object-fit: contain; flex-shrink: 0; }
.n { font-family: 'Spline Sans Mono', monospace; font-size: 13px; color: var(--txt-2); text-align: center; }
.n.pts { color: var(--txt); font-weight: 600; }
.err { color: #ff5a52; padding: 8px 0; }
.empty { color: var(--txt-2); font-size: 13.5px; padding: 16px 0; }

@media (max-width: 620px) {
  .thead, .trow { grid-template-columns: 24px 1fr 30px 40px 44px; }
  .hide-s { display: none; }
}
</style>
