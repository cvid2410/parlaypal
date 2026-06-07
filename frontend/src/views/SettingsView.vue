<template>
  <div class="settings">
    <p v-if="error" class="err">{{ error }}</p>

    <!-- Language -->
    <section>
      <div class="sect">{{ $t('settings.language') }}</div>
      <p class="hint">{{ $t('settings.language_hint') }}</p>
      <div class="chips">
        <button
          v-for="lng in SUPPORTED" :key="lng"
          class="chip" :class="{ on: locale === lng }"
          type="button" @click="setLang(lng)"
        >
          <span class="tick" aria-hidden="true">{{ locale === lng ? '✓' : '+' }}</span>
          {{ langName(lng) }}
        </button>
      </div>
    </section>

    <!-- Books -->
    <section>
      <div class="sect">{{ $t('settings.books_title') }}</div>
      <p class="hint">{{ $t('settings.books_hint') }}</p>
      <div class="chips">
        <button
          v-for="b in books" :key="b.key"
          class="chip" :class="{ on: selectedBooks.has(b.key) }"
          type="button" @click="toggle(selectedBooks, b.key)"
        >
          <span class="tick" aria-hidden="true">{{ selectedBooks.has(b.key) ? '✓' : '+' }}</span>
          <img
            class="blogo" :src="`/books/${b.key}.svg`" alt="" aria-hidden="true"
            @error="(e) => ((e.target as HTMLImageElement).style.display = 'none')"
          />
          {{ b.name }}
        </button>
      </div>
      <p class="note">{{ $t('settings.books_note') }}</p>
    </section>

    <!-- Leagues -->
    <section>
      <div class="sect">{{ $t('settings.leagues_title') }}</div>
      <p class="hint">{{ $t('settings.leagues_hint') }}</p>
      <div class="chips">
        <button
          v-for="l in leagues" :key="l.id"
          class="chip" :class="{ on: selectedLeagues.has(l.id) }"
          type="button" @click="toggle(selectedLeagues, l.id)"
        >
          <span class="tick" aria-hidden="true">{{ selectedLeagues.has(l.id) ? '✓' : '+' }}</span>
          {{ l.name }}<span v-if="l.is_soft" class="soft">{{ $t('settings.soft') }}</span>
        </button>
      </div>
      <p class="note">{{ $t('settings.leagues_note') }}</p>
    </section>

    <!-- Min edge -->
    <section>
      <div class="sect">{{ $t('settings.min_edge_title') }}</div>
      <p class="hint">{{ $t('settings.min_edge_hint') }}</p>
      <div class="edge">
        <input v-model.number="minEdge" type="number" min="0" step="0.5" inputmode="decimal" />
        <span class="pct">%</span>
      </div>
    </section>

    <div class="bar">
      <button class="save" type="button" :disabled="saving || !loaded" @click="save">
        {{ saving ? $t('settings.saving') : $t('settings.save') }}
      </button>
      <span v-if="saved" class="ok">{{ $t('settings.saved') }} ✓</span>
    </div>

    <p class="foot">{{ $t('settings.foot') }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { SUPPORTED, setLocale, type Locale } from '../i18n'

interface Book { key: string; name: string; promo?: string; url?: string; category?: string }
interface League { id: number; name: string; is_soft: boolean }

const auth = useAuthStore()
const router = useRouter()
const { t, locale } = useI18n()

const LANG_NAMES: Record<string, string> = { en: 'English', es: 'Español' }
const langName = (l: string) => LANG_NAMES[l] ?? l
function setLang(l: Locale) { setLocale(l) }

const books = ref<Book[]>([])
const leagues = ref<League[]>([])
const selectedBooks = ref<Set<string>>(new Set())
const selectedLeagues = ref<Set<number>>(new Set())
const minEdge = ref<number>(0)
const loaded = ref(false)
const saving = ref(false)
const saved = ref(false)
const error = ref('')

function toggle<T>(set: Set<T>, v: T) {
  saved.value = false
  if (set.has(v)) set.delete(v)
  else set.add(v)
}

async function load() {
  try {
    const [cfg, lgs, prefs] = await Promise.all([
      auth.authFetch('/config'),
      auth.authFetch('/leagues'),
      auth.authFetch('/me/preferences'),
    ])
    if ([cfg, lgs, prefs].some((r) => r.status === 401)) { router.push('/login'); return }
    if (!cfg.ok || !lgs.ok || !prefs.ok) throw new Error(t('settings.load_error'))
    books.value = (await cfg.json()).books
    leagues.value = (await lgs.json()).leagues
    const p = await prefs.json()
    selectedBooks.value = new Set(p.books)
    selectedLeagues.value = new Set(p.leagues)
    minEdge.value = p.min_edge ?? 0
    loaded.value = true
  } catch (e: any) { error.value = e.message }
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const res = await auth.authFetch('/me/preferences', {
      method: 'PUT',
      body: JSON.stringify({
        books: [...selectedBooks.value],
        leagues: [...selectedLeagues.value],
        min_edge: Number(minEdge.value) || 0,
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || 'Could not save')
    saved.value = true
  } catch (e: any) { error.value = e.message }
  finally { saving.value = false }
}

onMounted(() => {
  if (!auth.isAuthed) { router.push('/login'); return }
  load()
})
</script>

<style scoped>
.settings { color: var(--txt); max-width: 760px; }
section { margin-bottom: 30px; }
.sect { font-size: 11px; color: var(--txt-3); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 0 0 8px; }
.hint { font-size: 13px; color: var(--txt-2); line-height: 1.5; margin-bottom: 14px; }
.hint em { color: var(--txt); font-style: normal; font-weight: 700; }
.chips { display: flex; flex-wrap: wrap; gap: 10px; }
.chip { display: inline-flex; align-items: center; gap: 8px; padding: 10px 15px; border: 1px solid var(--hair); border-radius: 100px; background: var(--panel); color: var(--txt-2); font-size: 13.5px; font-weight: 600; cursor: pointer; transition: .15s; font-family: inherit; }
.chip:hover { border-color: var(--hair-2); color: var(--txt); }
.chip.on { background: var(--green-dim); border-color: var(--green); color: var(--txt); }
.chip .tick { font-size: 12px; color: var(--green); width: 12px; display: inline-flex; justify-content: center; }
.chip .blogo { height: 16px; width: auto; max-width: 22px; object-fit: contain; border-radius: 3px; }
.chip .soft { font-size: 9px; font-weight: 700; letter-spacing: .05em; color: var(--green); border: 1px solid var(--green-dim); padding: 1px 6px; border-radius: 100px; text-transform: uppercase; margin-left: 7px; }
.note { font-size: 11.5px; color: var(--txt-3); margin-top: 10px; }
.edge { display: flex; align-items: center; gap: 8px; }
.edge input { width: 110px; padding: 11px 14px; border: 1px solid var(--hair); border-radius: 11px; background: var(--panel); color: var(--txt); font-size: 15px; font-family: 'Spline Sans Mono', monospace; }
.edge input:focus { outline: none; border-color: var(--green); }
.edge .pct { color: var(--txt-3); font-size: 14px; }
.bar { display: flex; align-items: center; gap: 14px; border-top: 1px solid var(--hair); padding-top: 22px; }
.save { background: var(--green); color: #04210f; border: none; font-weight: 800; font-size: 13.5px; padding: 12px 22px; border-radius: 11px; cursor: pointer; text-transform: uppercase; letter-spacing: .3px; }
.save:disabled { opacity: .55; cursor: default; }
.ok { color: var(--green); font-size: 13px; font-weight: 600; }
.err { color: #ff5a52; padding: 8px 0; }
.foot { color: var(--txt-3); font-size: 11px; margin-top: 22px; line-height: 1.5; }
</style>
