<template>
  <div class="lgs">
    <div class="sect">{{ data ? `${data.count} leagues · ${data.live_total} signals live` : 'Leagues' }}</div>
    <p v-if="error" class="err">{{ error }}</p>

    <div v-for="lg in data?.leagues || []" :key="lg.id" class="lg2">
      <div class="nm">
        <b>{{ lg.name }}</b>
        <span v-if="lg.is_soft" class="soft">soft</span>
        <small>{{ lg.country }}{{ lg.is_soft ? '' : ' · sharp lines' }}</small>
      </div>
      <span class="cnt" :class="{ zero: lg.live_signals === 0 }">{{ lg.live_signals }}</span>
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
.lgs { max-width: 460px; margin: 0 auto; padding: 14px 12px 30px; color: #eef3f2; font-family: 'Archivo', sans-serif; }
.sect { font-size: 11px; color: #5f6f71; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 6px 4px 12px; }
.lg2 { display: flex; align-items: center; gap: 11px; padding: 11px 12px; background: #13191b; border: 1px solid #222d30; border-radius: 11px; margin-bottom: 8px; }
.lg2 .nm { flex: 1; }
.lg2 .nm b { font-size: 13px; font-weight: 700; }
.lg2 .nm small { font-size: 10.5px; color: #5f6f71; display: block; margin-top: 1px; }
.soft { font-size: 9px; font-weight: 800; letter-spacing: .4px; color: #ffc94d; background: #3a2f08; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; margin-left: 6px; }
.cnt { font-family: 'Spline Sans Mono', monospace; font-weight: 600; font-size: 13px; color: #1fd65f; background: #0e3f23; padding: 3px 9px; border-radius: 20px; }
.cnt.zero { color: #5f6f71; background: #1a2123; }
.err { color: #ff5a52; padding: 8px 4px; }
.empty { color: #8a9a9c; font-size: 13px; padding: 14px 4px; }
.foot { text-align: center; color: #5f6f71; font-size: 10.5px; margin-top: 16px; line-height: 1.5; }
</style>
