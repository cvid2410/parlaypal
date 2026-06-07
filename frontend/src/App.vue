<template>
  <div v-if="showChrome" class="app">
    <!-- sidebar (desktop) -->
    <aside class="side">
      <div class="brand"><span class="mark" aria-hidden="true" /><span class="wm">Parlay<span class="g">Pal</span></span></div>
      <nav class="nav" aria-label="Primary">
        <RouterLink v-for="t in tabs" :key="t.name" :to="t.path" class="navitem">
          <span class="ic" v-html="t.icon" aria-hidden="true" /> {{ $t('nav.' + t.name) }}
        </RouterLink>
      </nav>
      <div class="spacer" />
      <div class="upsell">
        <template v-if="!auth.isPaid">
          <h5>You're on Free</h5>
          <p>Signals are delayed and locked. Go Pro to see the pick, book and price - live.</p>
          <button class="go" @click="ui.openUpgrade()">Upgrade</button>
        </template>
        <template v-else>
          <h5>You're on <span class="g">{{ auth.tier }}</span></h5>
          <p>Live signals across every soft league are unlocked. 1-800-GAMBLER.</p>
        </template>
      </div>

      <footer class="sidefoot">
        <RouterLink to="/privacy">Privacy</RouterLink>
        <span class="sep" aria-hidden="true">·</span>
        <RouterLink to="/terms">Terms</RouterLink>
      </footer>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <h1 class="ttl">{{ titleKey ? $t('titles.' + titleKey + '.title') : 'ParlayPal' }}</h1>
          <div class="sub">{{ titleKey ? $t('titles.' + titleKey + '.sub') : '' }}</div>
        </div>
        <div class="right">
          <div class="pulse" :style="{ opacity: auth.isPaid ? 1 : .5 }"><span class="d" aria-hidden="true" /> Live</div>
          <button v-if="!auth.isPaid" class="badge free upbtn" @click="ui.openUpgrade()">free · upgrade</button>
          <span v-else class="badge pro">{{ auth.tier }}</span>
          <RouterLink class="iconbtn" to="/settings" title="Settings" aria-label="Settings"><span aria-hidden="true">⚙</span></RouterLink>
          <button class="iconbtn" @click="doLogout" title="Log out" aria-label="Log out"><span aria-hidden="true">⎋</span></button>
        </div>
      </header>
      <div class="content">
        <RouterView />
        <!-- mobile-only: the sidebar (with these links) is hidden under 900px -->
        <footer class="appfoot">
          <span>21+ · 1-800-GAMBLER</span>
          <RouterLink to="/privacy">Privacy</RouterLink>
          <span class="sep" aria-hidden="true">·</span>
          <RouterLink to="/terms">Terms</RouterLink>
        </footer>
      </div>
    </main>

    <!-- bottom nav (mobile) -->
    <nav class="mobnav" aria-label="Primary">
      <RouterLink v-for="t in tabs" :key="t.name" :to="t.path">
        <span class="ic" v-html="t.icon" aria-hidden="true" />{{ $t('nav.' + t.name) }}
      </RouterLink>
    </nav>

    <UpgradeModal />
  </div>

  <!-- auth wall / bare pages -->
  <div v-else class="bare">
    <RouterView />
    <footer v-if="route.name !== 'login'" class="mini-foot">
      21+ only. Gambling problem? Call 1-800-GAMBLER.
      · <RouterLink to="/privacy">Privacy</RouterLink> · <RouterLink to="/terms">Terms</RouterLink>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { useUiStore } from './stores/ui'
import UpgradeModal from './components/UpgradeModal.vue'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const route = useRoute()

const I = {
  signals: '<svg viewBox="0 0 24 24"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>',
  scores: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a9 9 0 0 0 0 18"/></svg>',
  ask: '<svg viewBox="0 0 24 24"><path d="M21 12a8 8 0 0 1-11.5 7.2L4 21l1.8-5.5A8 8 0 1 1 21 12z"/></svg>',
  leagues: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>',
}
const tabs = [
  { name: 'signals', path: '/signals', label: 'Signals', icon: I.signals },
  { name: 'scores', path: '/scores', label: 'Scores', icon: I.scores },
  { name: 'ask', path: '/ask', label: 'Ask', icon: I.ask },
  { name: 'leagues', path: '/leagues', label: 'Leagues', icon: I.leagues },
]

// Routes with a translated topbar title/subtitle (see i18n `titles.*`). Anything else
// falls back to the brand name.
const TITLE_KEYS = ['signals', 'scores', 'ask', 'leagues', 'league', 'lines', 'results', 'settings']
const titleKey = computed(() => {
  const n = route.name as string
  return TITLE_KEYS.includes(n) ? n : null
})

const showChrome = computed(() => auth.isAuthed && !['login', 'privacy', 'terms'].includes(route.name as string))

function doLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style>
:root {
  --bg: #06090b; --panel: #0c1112; --surface: #161f21; --surface-2: #1c2628;
  --hair: rgba(255, 255, 255, .07); --hair-2: rgba(255, 255, 255, .15);
  --txt: #eef3f2; --txt-2: #9aa6a8; --txt-3: #5f6f71;
  --green: #1fd65f; --green-dim: #0e3f23;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
html, body { height: 100%; }
body { background: var(--bg); color: var(--txt); font-family: 'Archivo', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
::-webkit-scrollbar { width: 9px; } ::-webkit-scrollbar-thumb { background: var(--hair-2); border-radius: 8px; }
a { text-decoration: none; }

.app { display: grid; grid-template-columns: 248px 1fr; height: 100vh; }

/* sidebar */
.side { border-right: 1px solid var(--hair); display: flex; flex-direction: column; padding: 22px 14px; background: var(--panel); }
.brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px 24px; }
.brand .mark { width: 10px; height: 10px; border-radius: 50%; background: var(--green); box-shadow: 0 0 10px var(--green); }
.brand .wm { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 19px; font-weight: 700; letter-spacing: -.02em; }
.brand .g { color: var(--green); }
.nav { display: flex; flex-direction: column; gap: 2px; }
.navitem { display: flex; align-items: center; gap: 13px; padding: 11px 12px; border-radius: 11px; color: var(--txt-2); font-size: 14.5px; font-weight: 600; transition: .15s; }
.navitem:hover { color: var(--txt); background: var(--surface); }
.navitem.router-link-active { color: var(--txt); background: var(--surface); }
.navitem.router-link-active .ic { color: var(--green); }
.navitem .ic { width: 19px; height: 19px; display: inline-flex; flex-shrink: 0; }
.navitem .ic svg { width: 19px; height: 19px; stroke: currentColor; fill: none; stroke-width: 1.7; }
.spacer { flex: 1; }
.upsell { border: 1px solid var(--hair); border-radius: 16px; padding: 16px; background: var(--bg); }
.upsell h5 { font-size: 13.5px; font-weight: 700; }
.upsell h5 .g { color: var(--green); text-transform: capitalize; }
.upsell p { font-size: 12px; color: var(--txt-3); margin: 6px 0 13px; line-height: 1.5; }
.upsell .go { width: 100%; background: var(--green); color: #04210f; border: none; font-weight: 800; font-size: 13px; padding: 10px; border-radius: 10px; cursor: pointer; text-transform: uppercase; letter-spacing: .3px; }
.sidefoot { display: flex; gap: 8px; padding: 14px 10px 2px; font-size: 11px; color: var(--txt-3); }
.sidefoot a { color: var(--txt-3); }
.sidefoot a:hover { color: var(--txt-2); }

/* main */
.main { overflow-y: auto; height: 100vh; }
.topbar { position: sticky; top: 0; z-index: 10; background: color-mix(in srgb, var(--bg) 80%, transparent); backdrop-filter: blur(14px); border-bottom: 1px solid var(--hair); padding: 20px 34px; display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; }
.topbar .ttl { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 28px; font-weight: 700; letter-spacing: -.02em; line-height: 1; }
.topbar .sub { font-size: 13px; color: var(--txt-3); margin-top: 8px; }
.topbar .right { display: flex; align-items: center; gap: 12px; }
.pulse { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--txt-2); font-weight: 600; }
.pulse .d { width: 7px; height: 7px; border-radius: 50%; background: var(--green); animation: pp 1.8s infinite; }
@keyframes pp { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
.badge { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; padding: 5px 10px; border-radius: 20px; }
.badge.free { background: var(--surface-2); color: var(--txt-2); }
.badge.pro { background: var(--green); color: #04210f; }
/* free badge as an upgrade button: keep the pill look, add affordance */
.badge.upbtn { border: 1px solid var(--green-dim); color: var(--green); cursor: pointer; font-family: inherit; transition: .15s; }
.badge.upbtn:hover { background: var(--green-dim); border-color: var(--green); }
.iconbtn { width: 36px; height: 36px; border-radius: 10px; border: 1px solid var(--hair); background: var(--panel); color: var(--txt-2); cursor: pointer; font-size: 16px; display: inline-flex; align-items: center; justify-content: center; }
.iconbtn:hover { color: var(--txt); border-color: var(--hair-2); }
.content { padding: 28px 34px 70px; }
.appfoot { display: none; }

/* mobile bottom nav (hidden on desktop) */
.mobnav { display: none; }
.bare { min-height: 100vh; display: flex; flex-direction: column; }
.bare .mini-foot { text-align: center; color: var(--txt-3); font-size: 11px; padding: 16px; }
.bare .mini-foot a { color: var(--txt-2); }

@media (max-width: 900px) {
  .app { grid-template-columns: 1fr; height: auto; min-height: 100vh; }
  .side { display: none; }
  .main { height: auto; overflow: visible; }
  .topbar { padding: 16px 16px; }
  .topbar .ttl { font-size: 23px; }
  .content { padding: 18px 14px 90px; }
  .mobnav { display: flex; position: fixed; bottom: 0; left: 0; right: 0; z-index: 40; background: color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter: blur(16px); border-top: 1px solid var(--hair); padding: 8px 4px 11px; }
  .mobnav a { flex: 1; color: var(--txt-3); font-size: 9.5px; font-weight: 600; padding: 6px 2px; display: flex; flex-direction: column; align-items: center; gap: 5px; text-transform: uppercase; letter-spacing: .3px; }
  .mobnav a .ic { width: 20px; height: 20px; }
  .mobnav a .ic svg { width: 20px; height: 20px; stroke: currentColor; fill: none; stroke-width: 1.6; }
  .mobnav a.router-link-active { color: var(--green); }
  .appfoot { display: flex; flex-wrap: wrap; align-items: center; gap: 9px; margin-top: 30px; padding-top: 16px; border-top: 1px solid var(--hair); font-size: 11px; color: var(--txt-3); }
  .appfoot a { color: var(--txt-2); }
  .appfoot a:hover { color: var(--txt); }
}
</style>
