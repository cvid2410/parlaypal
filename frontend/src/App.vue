<template>
  <div class="app">
    <header class="site-header">
      <nav class="nav">
        <RouterLink to="/" class="logo">parlaypal<span>.gg</span></RouterLink>
        <div class="nav-links">
          <RouterLink to="/">Schedule</RouterLink>
          <RouterLink to="/parlay">My Parlay</RouterLink>
        </div>
      </nav>
    </header>
    <main class="main-content">
      <RouterView />
    </main>
    <footer class="site-footer">
      <p class="disclaimer">21+ only. Gambling problem? Call 1-800-GAMBLER.</p>
    </footer>
  </div>
</template>

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

.logo { font-size: 1.25rem; font-weight: 700; color: var(--green); }
.logo span { color: var(--text); }

.nav-links { display: flex; gap: 1.5rem; }
.nav-links a { color: var(--muted); font-size: 0.9rem; transition: color 0.15s; white-space: nowrap; }
.nav-links a:hover, .nav-links a.router-link-active { color: var(--text); }

@media (max-width: 400px) {
  .nav { gap: 1rem; }
  .nav-links { gap: 1rem; }
  .nav-links a { font-size: 0.82rem; }
}

.main-content { flex: 1; max-width: 1200px; margin: 0 auto; padding: 1.5rem 1rem; width: 100%; }

.site-footer {
  border-top: 1px solid var(--border);
  padding: 1rem;
  text-align: center;
}

.disclaimer { font-size: 0.75rem; color: var(--muted); }
</style>
