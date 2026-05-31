<template>
  <div class="app">
    <header v-if="showChrome" class="apphead">
      <span class="dot" />
      <RouterLink to="/signals" class="brand">Parlay<span>Pal</span></RouterLink>
      <span class="badge" :class="auth.isPaid ? 'pro' : 'free'">{{ auth.tier }}</span>
      <button class="logout" @click="doLogout" title="Log out">⎋</button>
    </header>

    <main class="content">
      <RouterView />
    </main>

    <nav v-if="showChrome" class="tabbar">
      <RouterLink to="/scores"><span class="i">⚽</span>Scores</RouterLink>
      <RouterLink to="/signals"><span class="i">⚡</span>Signals</RouterLink>
      <RouterLink to="/ask"><span class="i">💬</span>Ask</RouterLink>
      <RouterLink to="/results"><span class="i">📈</span>Results</RouterLink>
      <RouterLink to="/leagues"><span class="i">🌍</span>Leagues</RouterLink>
    </nav>

    <footer v-else class="mini-foot">
      21+ only. Gambling problem? Call 1-800-GAMBLER.
      · <RouterLink to="/privacy">Privacy</RouterLink> · <RouterLink to="/terms">Terms</RouterLink>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

// App chrome (brand bar + tab bar) only when signed in and inside the product.
const showChrome = computed(() => auth.isAuthed && !['login'].includes(route.name as string))

function doLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
body { background: #05080a; color: #eef3f2; font-family: 'Archivo', -apple-system, BlinkMacSystemFont, sans-serif; min-height: 100vh; }
#app { min-height: 100vh; }
.app { display: flex; flex-direction: column; min-height: 100vh; background-image: radial-gradient(circle at 50% 0%, #0e1618, #05080a 60%); }

.apphead { position: sticky; top: 0; z-index: 10; display: flex; align-items: center; gap: 9px; padding: 13px 16px; border-bottom: 1px solid #222d30; background: #0a0e0f; }
.apphead .dot { width: 9px; height: 9px; border-radius: 50%; background: #1fd65f; box-shadow: 0 0 10px #1fd65f; }
.brand { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-weight: 700; font-size: 18px; letter-spacing: .5px; text-transform: uppercase; text-decoration: none; color: #eef3f2; }
.brand span { color: #1fd65f; }
.apphead .badge { margin-left: auto; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; padding: 4px 10px; border-radius: 20px; }
.apphead .badge.free { background: #1a2123; color: #8a9a9c; }
.apphead .badge.pro { background: #ffc94d; color: #241a00; }
.apphead .logout { background: none; border: none; color: #5f6f71; font-size: 18px; cursor: pointer; padding: 0 2px; }

.content { flex: 1; padding-bottom: 70px; }

.tabbar { position: fixed; bottom: 0; left: 0; right: 0; display: flex; border-top: 1px solid #222d30; background: #0c1112; z-index: 10; }
.tabbar a { flex: 1; text-decoration: none; color: #5f6f71; font-size: 9.5px; font-weight: 600; padding: 9px 2px 11px; display: flex; flex-direction: column; align-items: center; gap: 4px; text-transform: uppercase; letter-spacing: .3px; }
.tabbar a .i { font-size: 18px; line-height: 1; }
.tabbar a.router-link-active { color: #1fd65f; }

.mini-foot { text-align: center; color: #5f6f71; font-size: 11px; padding: 16px; line-height: 1.6; }
.mini-foot a { color: #8a9a9c; }
</style>
