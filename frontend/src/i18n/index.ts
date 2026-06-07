import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import es from './locales/es.json'

// Supported UI locales. Spanish first because the audience is CONCACAF / South-American
// soccer; add pt (Brazil) etc. as locale files land. (Static UI only - the compliance-
// sensitive signal copy is server-side and translated separately, see copy.py.)
export const SUPPORTED = ['en', 'es'] as const
export type Locale = (typeof SUPPORTED)[number]

const STORAGE_KEY = 'locale'

function detectLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && (SUPPORTED as readonly string[]).includes(saved)) return saved as Locale
  const nav = (navigator.language || 'en').slice(0, 2)
  return (SUPPORTED as readonly string[]).includes(nav) ? (nav as Locale) : 'en'
}

export const i18n = createI18n({
  legacy: false, // Composition API
  globalInjection: true, // $t available in every template
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages: { en, es },
})

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale
}

// Apply the detected locale to <html lang> on boot (for a11y + browser hints).
document.documentElement.lang = i18n.global.locale.value
