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
  const cardH2H = ref<Record<number, OddsLine[]>>({})
  const cardH2HLoading = ref(false)

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

  async function fetchCardH2H() {
    if (Object.keys(cardH2H.value).length > 0 || cardH2HLoading.value) return
    cardH2HLoading.value = true
    try {
      const res = await fetch('/api/odds/h2h')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: Record<string, OddsLine[]> = await res.json()
      cardH2H.value = Object.fromEntries(
        Object.entries(data).map(([k, v]) => [Number(k), v])
      )
    } catch {
      // fail silently — cards just won't show odds
    } finally {
      cardH2HLoading.value = false
    }
  }

  function getOdds(matchId: number, market: string): OddsLine[] {
    return (cache.value[matchId] ?? []).filter(o => o.market === market)
  }

  function getCardOdds(matchId: number): OddsLine[] {
    return cardH2H.value[matchId] ?? []
  }

  return { cache, loading, cardH2HLoading, fetchOdds, fetchCardH2H, getOdds, getCardOdds }
})
