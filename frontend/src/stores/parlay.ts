import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Match } from './matches'

export interface Pick {
  id: string          // `${match_id}:${market}:${selection}:${book}`
  match_id: number
  label: string
  odds: string        // American format: "-110", "+200"
  market: string
  book: string
}

export interface HistoryEntry {
  id: string
  date: string        // ISO timestamp
  picks: Pick[]
  stake: number
  payout: number
  status: 'pending' | 'won' | 'lost'
}

const STAKES = [25, 50, 100, 250] as const
export type Stake = typeof STAKES[number]

function americanToDecimal(odds: string): number {
  const n = parseInt(odds, 10)
  if (n > 0) return n / 100 + 1
  return 100 / Math.abs(n) + 1
}

const STORAGE_KEY = 'parlaypal:picks'
const HISTORY_KEY = 'parlaypal:history'

export const useParlayStore = defineStore('parlay', () => {
  const picks = ref<Pick[]>(loadFromStorage())
  const stake = ref<Stake>(25)
  const history = ref<HistoryEntry[]>(loadHistory())

  const multiplier = computed(() => {
    if (picks.value.length === 0) return 1
    return picks.value.reduce((acc, p) => acc * americanToDecimal(p.odds), 1)
  })

  const payout = computed(() => +(stake.value * multiplier.value).toFixed(2))
  const profit = computed(() => +(payout.value - stake.value).toFixed(2))

  function hasPick(id: string) {
    return picks.value.some(p => p.id === id)
  }

  function addPick(pick: Pick) {
    // One pick per match (remove any existing pick for same match)
    picks.value = picks.value.filter(p => p.match_id !== pick.match_id || p.market !== pick.market)
    picks.value.push(pick)
    persist()
  }

  function removePick(id: string) {
    picks.value = picks.value.filter(p => p.id !== id)
    persist()
  }

  function clear() {
    picks.value = []
    persist()
  }

  function setStake(s: Stake) {
    stake.value = s
  }

  function persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(picks.value))
  }

  function saveCurrent() {
    if (!picks.value.length) return
    const entry: HistoryEntry = {
      id: `${Date.now()}`,
      date: new Date().toISOString(),
      picks: [...picks.value],
      stake: stake.value,
      payout: payout.value,
      status: 'pending',
    }
    history.value.unshift(entry)
    if (history.value.length > 10) history.value.length = 10
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
    picks.value = []
    persist()
  }

  function clearHistory() {
    history.value = []
    localStorage.removeItem(HISTORY_KEY)
  }

  function checkResults(matches: Match[]) {
    let changed = false
    for (const entry of history.value) {
      if (entry.status !== 'pending') continue
      const entryMatches = entry.picks.map(p => matches.find(m => m.id === p.match_id))
      if (entryMatches.some(m => !m || m.status !== 'finished' || m.home_score == null)) continue
      const results = entry.picks.map(p => evaluatePick(p, entryMatches.find(m => m!.id === p.match_id)!))
      if (results.some(r => r === null)) continue
      entry.status = results.every(Boolean) ? 'won' : 'lost'
      changed = true
    }
    if (changed) localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
  }

  return { picks, stake, multiplier, payout, profit, history, STAKES, hasPick, addPick, removePick, clear, setStake, saveCurrent, clearHistory, checkResults }
})

function evaluatePick(pick: Pick, match: Match): boolean | null {
  const home = match.home_score!
  const away = match.away_score!
  const selection = pick.id.split(':')[2]

  if (pick.market === 'h2h') {
    const homeSlug = match.home_team.toLowerCase().replace(/\s+/g, '_')
    const awaySlug = match.away_team.toLowerCase().replace(/\s+/g, '_')
    if (home > away) return selection === homeSlug
    if (away > home) return selection === awaySlug
    return selection === 'draw'
  }

  if (pick.market === 'totals') {
    const total = home + away
    const parts = selection.split('_')
    const direction = parts[0]
    const point = parseFloat(parts.slice(1).join('.'))
    if (isNaN(point)) return null
    if (direction === 'over') return total > point
    if (direction === 'under') return total < point
    return null
  }

  if (pick.market === 'btts') {
    const btts = home > 0 && away > 0
    return selection === 'yes' ? btts : !btts
  }

  return null // corners, shots, cards — no data to evaluate
}

function loadFromStorage(): Pick[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}
