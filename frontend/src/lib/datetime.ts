import { i18n } from '../i18n'

// Kickoff formatters. Locale-aware (uses the active i18n locale) and they ALWAYS include the
// year - important across a multi-week event like the World Cup, where "Sun, 3:00 PM" alone
// doesn't tell you if it's June 11 or July 19.

export function kickoffLong(iso: string): string {
  return new Date(iso).toLocaleString(i18n.global.locale.value, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

// Date only (no time) + year, for past-game date stamps.
export function dateLong(iso: string): string {
  return new Date(iso).toLocaleDateString(i18n.global.locale.value, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// Compact time only (for same-day contexts like the Scores tab).
export function timeShort(iso: string): string {
  return new Date(iso).toLocaleTimeString(i18n.global.locale.value, {
    hour: 'numeric',
    minute: '2-digit',
  })
}
