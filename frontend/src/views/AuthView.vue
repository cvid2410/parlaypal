<template>
  <div class="auth">
    <!-- pitch panel (desktop): show the product, don't just describe it -->
    <aside class="pitch">
      <div class="brand"><span class="mark" aria-hidden="true" /><span class="wm">Parlay<span class="g">Pal</span></span></div>

      <div class="pitchbody">
        <h1>Every edge in soccer, <span class="g">first</span>.</h1>
        <p class="tag">Live value bets, arbs and best prices across every league — including the soft ones the big tools don't even cover.</p>

        <div class="preview" aria-hidden="true">
          <div class="live"><span class="dot" /> signals the moment a line goes soft</div>
          <div class="stack">
            <div v-for="(s, i) in samples" :key="i" class="minicard" :class="s.kind">
              <div class="row">
                <span class="badge">{{ s.badge }}</span>
                <span class="lg">{{ s.lg }}</span>
                <span class="ago">{{ s.ago }}</span>
              </div>
              <div class="body">
                <div class="info">
                  <div class="pick">{{ s.pick }}</div>
                  <div class="fx">{{ s.fx }}</div>
                </div>
                <div class="metric">
                  <div class="v">{{ s.metric }}</div>
                  <div class="k">{{ s.label }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <p class="rg">21+ · For entertainment, not financial advice · 1-800-GAMBLER</p>
    </aside>

    <!-- form panel -->
    <main class="formpane">
      <div class="card">
        <div class="brand mob"><span class="mark" aria-hidden="true" /><span class="wm">Parlay<span class="g">Pal</span></span></div>
        <h2>{{ mode === 'login' ? 'Welcome back' : 'Create your account' }}</h2>
        <p class="sub">{{ mode === 'login' ? 'Log in to see live signals.' : 'Free to start — live scores and locked signal teasers.' }}</p>

        <form @submit.prevent="submit">
          <label>Email
            <input v-model="email" type="email" placeholder="you@email.com" autocomplete="email" required />
          </label>
          <label>Password
            <input v-model="password" type="password" placeholder="8+ characters" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" required />
          </label>
          <button class="primary" :disabled="loading" type="submit">
            {{ loading ? '…' : (mode === 'login' ? 'Log in' : 'Sign up free') }}
          </button>
        </form>

        <p v-if="error" class="err">{{ error }}</p>

        <p class="switch">
          {{ mode === 'login' ? "Don't have an account?" : 'Already have one?' }}
          <button type="button" class="link" @click="toggle">{{ mode === 'login' ? 'Sign up' : 'Log in' }}</button>
        </p>
      </div>

      <footer class="legal">
        <span class="mob-rg">21+ · 1-800-GAMBLER</span>
        <RouterLink to="/privacy">Privacy</RouterLink>
        <span class="sep" aria-hidden="true">·</span>
        <RouterLink to="/terms">Terms</RouterLink>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Static, illustrative sample signals for the pitch panel — one of each type so
// new users see the range. EV lives on soft leagues; arbs/middles are mechanical
// and span every league (incl. the big ones), matching how the product works.
const samples = [
  { kind: 'ev', badge: 'Value bet', pick: 'Pumas −0.5', fx: 'Pumas vs Necaxa', lg: 'Liga MX · Mexico', metric: '+4.8%', label: 'your edge', ago: '2m' },
  { kind: 'arb', badge: 'Arbitrage', pick: 'Win either way', fx: 'Inter vs Milan', lg: 'Serie A · Italy', metric: '+2.1%', label: 'locked profit', ago: '5m' },
  { kind: 'middle', badge: 'Middle', pick: 'Over 2.5 / Under 3.5', fx: 'Palmeiras vs Grêmio', lg: 'Série A · Brazil', metric: '+6.0%', label: 'middle upside', ago: '8m' },
]

const auth = useAuthStore()
const router = useRouter()
const mode = ref<'login' | 'signup'>('signup')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

function toggle() {
  mode.value = mode.value === 'login' ? 'signup' : 'login'
  error.value = ''
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (mode.value === 'login') await auth.login(email.value, password.value)
    else await auth.signup(email.value, password.value)
    router.push('/signals')
  } catch (e: any) {
    error.value = e.message || 'Something went wrong'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth { display: grid; grid-template-columns: 1.05fr 1fr; min-height: 100vh; }

/* pitch */
.pitch { background: var(--panel); border-right: 1px solid var(--hair); padding: 40px 44px; display: flex; flex-direction: column;
  background-image: radial-gradient(circle at 18% 10%, rgba(31, 214, 95, .12), transparent 46%); }
.brand { display: flex; align-items: center; gap: 11px; }
.brand .mark { width: 11px; height: 11px; border-radius: 50%; background: var(--green); box-shadow: 0 0 12px var(--green); }
.brand .wm { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 22px; font-weight: 700; letter-spacing: -.02em; }
.brand .g { color: var(--green); }
.pitchbody { flex: 1; display: flex; flex-direction: column; justify-content: center; max-width: 470px; }
.pitchbody h1 { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 42px; line-height: 1.05; font-weight: 700; letter-spacing: -.02em; }
.pitchbody h1 .g { color: var(--green); }
.tag { color: var(--txt-2); font-size: 15px; line-height: 1.55; margin-top: 16px; }

/* product preview — a static stack of sample signals, one per type, mirroring
   the Signals cards (accent spine + badge keyed to kind). */
.preview { margin-top: 28px; }
.live { display: flex; align-items: center; gap: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--txt-3); margin-bottom: 12px; }
.live .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); animation: lp 1.8s infinite; }
@keyframes lp { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }
.stack { display: flex; flex-direction: column; gap: 10px; }

.minicard { position: relative; border: 1px solid var(--hair); border-radius: 14px; padding: 14px 16px 14px 18px; background: var(--bg); overflow: hidden; }
.minicard::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent, var(--hair-2)); }
.minicard.ev { --accent: var(--green); }
.minicard.arb { --accent: var(--hair-2); }
.minicard.middle { --accent: #5cb3ff; }
.minicard .row { display: flex; align-items: center; gap: 9px; margin-bottom: 11px; }
.minicard .badge { font-size: 9.5px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 100px; }
.minicard.ev .badge { background: var(--green-dim); color: var(--green); }
.minicard.arb .badge { background: var(--surface-2); color: var(--txt); border: 1px solid var(--hair-2); }
.minicard.middle .badge { background: #0c2536; color: #5cb3ff; }
.minicard .lg { font-size: 11px; color: var(--txt-3); }
.minicard .ago { margin-left: auto; font-family: 'Spline Sans Mono', monospace; font-size: 11px; color: var(--txt-3); }
.minicard .body { display: flex; align-items: center; gap: 12px; }
.minicard .info { flex: 1; min-width: 0; }
.minicard .pick { font-size: 17px; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; }
.minicard .fx { font-size: 11.5px; color: var(--txt-3); margin-top: 4px; }
.minicard .metric { text-align: right; flex-shrink: 0; }
.minicard .metric .v { font-family: 'Spline Sans Mono', monospace; font-size: 18px; font-weight: 600; color: var(--green); line-height: 1; }
.minicard .metric .k { font-size: 9px; color: var(--txt-3); text-transform: uppercase; letter-spacing: .05em; margin-top: 5px; font-weight: 700; white-space: nowrap; }

.rg { color: var(--txt-3); font-size: 11.5px; }

/* form */
.formpane { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 22px; padding: 40px 24px; }
.card { width: 100%; max-width: 392px; background: var(--panel); border: 1px solid var(--hair); border-radius: 20px; padding: 34px 32px; box-shadow: 0 18px 50px rgba(0, 0, 0, .4); }
.brand.mob { display: none; margin-bottom: 22px; }
.card h2 { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 28px; font-weight: 700; letter-spacing: -.02em; }
.sub { color: var(--txt-2); font-size: 13.5px; margin: 8px 0 24px; line-height: 1.5; }
form { display: flex; flex-direction: column; gap: 15px; }
label { display: flex; flex-direction: column; gap: 7px; font-size: 12px; font-weight: 600; color: var(--txt-2); text-transform: uppercase; letter-spacing: .05em; }
input { background: var(--bg); border: 1px solid var(--hair); border-radius: 11px; padding: 13px 15px; color: var(--txt); font-size: 14px; font-family: inherit; font-weight: 400; text-transform: none; letter-spacing: normal; transition: border-color .15s; }
input::placeholder { color: var(--txt-3); }
input:focus { outline: none; border-color: var(--green); }
.primary { background: var(--green); color: #04210f; border: none; font-weight: 800; font-size: 14px; padding: 14px; border-radius: 11px; cursor: pointer; text-transform: uppercase; letter-spacing: .4px; margin-top: 4px; transition: filter .15s; }
.primary:hover:not(:disabled) { filter: brightness(1.08); }
.primary:disabled { opacity: .6; cursor: default; }
.err { color: #ff5a52; font-size: 12.5px; margin-top: 12px; }
.switch { color: var(--txt-2); font-size: 13.5px; margin-top: 20px; }
.switch .link { color: var(--green); font-weight: 600; background: none; border: none; padding: 0; cursor: pointer; font-size: inherit; }
.switch .link:hover { text-decoration: underline; }

.legal { display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--txt-3); }
.legal a { color: var(--txt-2); }
.legal a:hover { color: var(--txt); }
.legal .mob-rg { display: none; }
.legal .mob-rg::after { content: '·'; margin-left: 10px; color: var(--txt-3); }

@media (max-width: 820px) {
  .auth { grid-template-columns: 1fr; }
  .pitch { display: none; }
  .formpane { padding: 32px 18px; align-items: flex-start; padding-top: 12vh; }
  .brand.mob { display: flex; }
  /* pitch (with its 1-800-GAMBLER line) is hidden here, so surface it in the footer */
  .legal .mob-rg { display: inline; }
}
</style>
