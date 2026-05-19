<template>
  <div class="app">
    <header class="site-header">
      <nav class="nav">
        <RouterLink to="/" class="logo">parlaypal<span>.gg</span></RouterLink>
        <div class="nav-links">
          <RouterLink to="/">Schedule</RouterLink>
          <RouterLink to="/standings">Standings</RouterLink>
          <RouterLink to="/bracket">Bracket</RouterLink>
          <RouterLink to="/parlay" class="parlay-link">
            My Parlay
            <span v-if="parlay.picks.length" class="pick-badge">{{ parlay.picks.length }}</span>
          </RouterLink>
        </div>
      </nav>
    </header>
    <main class="main-content">
      <RouterView />
    </main>
    <footer class="site-footer">
      <p class="disclaimer">21+ only. Gambling problem? Call 1-800-GAMBLER.</p>
      <div class="footer-links">
        <RouterLink to="/privacy">Privacy Policy</RouterLink>
        <span aria-hidden="true">·</span>
        <RouterLink to="/terms">Terms of Service</RouterLink>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useParlayStore } from './stores/parlay'
const parlay = useParlayStore()
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --green: #00c853;
  --dark: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --radius: 8px;
}

body {
  background: var(--dark);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  min-height: 100vh;
}

a { color: inherit; text-decoration: none; }

.app { display: flex; flex-direction: column; min-height: 100vh; }

.site-header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 2rem;
}

.logo { font-size: 1.25rem; font-weight: 700; color: var(--green); flex-shrink: 0; }
.logo span { color: var(--text); }

.nav-links {
  display: flex;
  gap: 1.5rem;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.nav-links::-webkit-scrollbar { display: none; }
.nav-links a { color: var(--muted); font-size: 0.9rem; transition: color 0.15s; white-space: nowrap; }
.nav-links a:hover, .nav-links a.router-link-active { color: var(--text); }

.parlay-link { display: flex; align-items: center; gap: 6px; }

.pick-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--green);
  color: #000;
  font-size: 0.65rem;
  font-weight: 700;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 999px;
}

@media (max-width: 600px) {
  .nav {
    height: auto;
    flex-wrap: wrap;
    gap: 0;
    padding: 0.5rem 1rem 0;
  }
  .logo { padding: 0.25rem 0; font-size: 1.1rem; }
  .nav-links {
    flex-basis: 100%;
    gap: 1.25rem;
    padding: 0.4rem 0 0.5rem;
  }
}

.main-content { flex: 1; max-width: 1200px; margin: 0 auto; padding: 1.5rem 1rem; width: 100%; }

.site-footer {
  border-top: 1px solid var(--border);
  padding: 1rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.disclaimer { font-size: 0.75rem; color: var(--muted); }

.footer-links {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--muted);
}

.footer-links a { color: var(--muted); }
.footer-links a:hover { color: var(--text); }
</style>
