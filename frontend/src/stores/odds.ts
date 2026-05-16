import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface OddsLine {
  market: string
  selection: string
  odds: string
  book: string
  description: string
  point: number | null
}

export const useOddsStore = defineStore('odds', () => {
  const cache = ref<Record<number, OddsLine[]>>({})
  const loading = ref<Record<number, boolean>>({})

  async function fetchOdds(matchId: number) {
    if (cache.value[matchId]) return
    loading.value[matchId] = true
    try {
      const res = await fetch(`/api/odds?match_id=${matchId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      cache.value[matchId] = await res.json()
    } catch {
      cache.value[matchId] = []
    } finally {
      loading.value[matchId] = false
    }
  }

  function getOdds(matchId: number, market: string): OddsLine[] {
    return (cache.value[matchId] ?? []).filter(o => o.market === market)
  }

  return { cache, loading, fetchOdds, getOdds }
})
