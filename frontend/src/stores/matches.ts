import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Match {
  id: number
  date: string
  home_team: string
  away_team: string
  home_flag: string
  away_flag: string
  group: string
  venue: string
  city: string
  status: 'scheduled' | 'live' | 'finished'
  home_score?: number
  away_score?: number
}

export type Timezone = 'ET' | 'CT' | 'MT' | 'PT'

export const TEAM_GROUP: Record<string, string> = {
  'Algeria': 'A', 'Argentina': 'A', 'Austria': 'A', 'Jordan': 'A',
  'Belgium': 'B', 'Egypt': 'B', 'Iran': 'B', 'New Zealand': 'B',
  'Brazil': 'C', 'Haiti': 'C', 'Morocco': 'C', 'Scotland': 'C',
  'Bosnia & Herzegovina': 'D', 'Canada': 'D', 'Qatar': 'D', 'Switzerland': 'D',
  'Croatia': 'E', 'England': 'E', 'Ghana': 'E', 'Panama': 'E',
  'France': 'F', 'Iraq': 'F', 'Norway': 'F', 'Senegal': 'F',
  'Curaçao': 'G', 'Ecuador': 'G', 'Germany': 'G', 'Ivory Coast': 'G',
  'Czech Republic': 'H', 'Mexico': 'H', 'South Africa': 'H', 'South Korea': 'H',
  'Japan': 'I', 'Netherlands': 'I', 'Sweden': 'I', 'Tunisia': 'I',
  'Colombia': 'J', 'Congo DR': 'J', 'Portugal': 'J', 'Uzbekistan': 'J',
  'Cape Verde Islands': 'K', 'Saudi Arabia': 'K', 'Spain': 'K', 'Uruguay': 'K',
  'Australia': 'L', 'Paraguay': 'L', 'Türkiye': 'L', 'USA': 'L',
}

const TZ_OFFSETS: Record<Timezone, string> = {
  ET: 'America/New_York',
  CT: 'America/Chicago',
  MT: 'America/Denver',
  PT: 'America/Los_Angeles',
}

export const useMatchesStore = defineStore('matches', () => {
  const matches = ref<Match[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedTeam = ref('')
  const selectedTimezone = ref<Timezone>('ET')

  const allTeams = computed(() => {
    const teams = new Set<string>()
    for (const m of matches.value) {
      teams.add(m.home_team)
      teams.add(m.away_team)
    }
    return [...teams].sort()
  })

  const filtered = computed(() => {
    if (!selectedTeam.value) return matches.value
    return matches.value.filter(m =>
      m.home_team === selectedTeam.value || m.away_team === selectedTeam.value
    )
  })

  function formatMatchTime(dateStr: string): string {
    return new Intl.DateTimeFormat('en-US', {
      timeZone: TZ_OFFSETS[selectedTimezone.value],
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(dateStr))
  }

  async function loadMatches() {
    loading.value = true
    error.value = null
    try {
      const res = await fetch('/api/matches')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      matches.value = await res.json()
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
    }
  }

  return { matches, loading, error, selectedTeam, selectedTimezone, allTeams, filtered, formatMatchTime, loadMatches }
})
