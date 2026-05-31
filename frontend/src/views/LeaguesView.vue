<template>
  <div class="lgs">
    <div class="sect">{{ data ? `${data.count} covered · ${data.live_total} signals live now` : 'Leagues' }}</div>
    <p v-if="error" class="err">{{ error }}</p>

    <div class="list">
      <div v-for="lg in data?.leagues || []" :key="lg.id" class="lgrow">
        <div class="info">
          <b>{{ lg.name }} <span v-if="lg.is_soft" class="soft">soft</span></b>
          <small>{{ lg.country }}{{ lg.is_soft ? ' · books lag here' : ' · sharp lines, no edge' }}</small>
        </div>
        <span class="c" :class="{ z: lg.live_signals === 0 }">{{ lg.live_signals }}</span>
      </div>
    </div>

    <p v-if="data && data.leagues.length === 0" class="empty">No leagues configured.</p>
    <p class="foot">Soft = books lag, the edge lives here. Sharp leagues are scores-only. 1-800-GAMBLER.</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface L { id: number; name: string; country: string; is_soft: boolean; live_signals: number }
interface Leagues { count: number; live_total: number; leagues: L[] }

const auth = useAuthStore()
const router = useRouter()
const data = ref<Leagues | null>(null)
const error = ref('')

async function load() {
  try {
    const res = await auth.authFetch('/leagues')
    if (res.status === 401) { router.push('/login'); return }
    if (!res.ok) throw new Error('Failed to load leagues')
    data.value = await res.json()
  } catch (e: any) { error.value = e.message }
}

onMounted(() => {
  if (!auth.isAuthed) { router.push('/login'); return }
  load()
})
</script>

<style scoped>
.lgs { color: var(--txt); max-width: 760px; }
.sect { font-size: 11px; color: var(--txt-3); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 0 0 14px; }
.list { display: flex; flex-direction: column; gap: 10px; }
.lgrow { display: flex; align-items: center; gap: 16px; padding: 17px 20px; border: 1px solid var(--hair); border-radius: 14px; background: var(--panel); transition: .18s; }
.lgrow:hover { transform: translateY(-1px); border-color: var(--hair-2); }
.lgrow .info { flex: 1; }
.lgrow .info b { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 9px; letter-spacing: -.01em; }
.lgrow .info small { font-size: 12px; color: var(--txt-3); display: block; margin-top: 3px; }
.soft { font-size: 9.5px; font-weight: 700; letter-spacing: .05em; color: var(--green); border: 1px solid var(--green-dim); padding: 2px 8px; border-radius: 100px; text-transform: uppercase; }
.c { font-family: 'Spline Sans Mono', monospace; font-size: 15px; font-weight: 600; color: var(--green); }
.c.z { color: var(--txt-3); }
.err { color: #ff5a52; padding: 8px 0; }
.empty { color: var(--txt-2); font-size: 13.5px; padding: 14px 0; }
.foot { color: var(--txt-3); font-size: 11px; margin-top: 18px; line-height: 1.5; }
</style>
