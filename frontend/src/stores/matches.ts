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
  const selectedGroup = ref('all')
  const selectedTimezone = ref<Timezone>('ET')

  const filtered = computed(() => {
    if (selectedGroup.value === 'all') return matches.value
    return matches.value.filter(m =>
      m.group.toUpperCase().includes(selectedGroup.value.toUpperCase())
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
      const res = await fetch(`/api/matches?group=${selectedGroup.value}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      matches.value = await res.json()
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
    }
  }

  return { matches, loading, error, selectedGroup, selectedTimezone, filtered, formatMatchTime, loadMatches }
})
