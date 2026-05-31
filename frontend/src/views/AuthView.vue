<template>
  <div class="auth">
    <!-- pitch panel (desktop) -->
    <aside class="pitch">
      <div class="brand"><span class="mark" /><span class="wm">Parlay<span class="g">Pal</span></span></div>
      <div class="pitchbody">
        <h1>The only betting-edge tool built <span class="g">only for soccer</span>.</h1>
        <p class="tag">Every league on earth — including the soft ones the big tools don't even cover.</p>
        <ul class="feats">
          <li><span class="ck">✓</span> Live value bets &amp; arbs the moment a line goes soft</li>
          <li><span class="ck">✓</span> The soft long tail — Liga MX, Brazil, J-League, Honduras</li>
          <li><span class="ck">✓</span> Priced against the sharp closing line, not guesswork</li>
        </ul>
      </div>
      <p class="rg">21+ · For entertainment, not financial advice · 1-800-GAMBLER</p>
    </aside>

    <!-- form panel -->
    <main class="formpane">
      <div class="form">
        <div class="brand mob"><span class="mark" /><span class="wm">Parlay<span class="g">Pal</span></span></div>
        <h2>{{ mode === 'login' ? 'Welcome back' : 'Create your account' }}</h2>
        <p class="sub">{{ mode === 'login' ? 'Log in to see live signals.' : 'Free to start — see live scores and locked signal teasers.' }}</p>

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
          <a href="#" @click.prevent="toggle">{{ mode === 'login' ? 'Sign up' : 'Log in' }}</a>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

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
  background-image: radial-gradient(circle at 18% 12%, rgba(31, 214, 95, .10), transparent 42%); }
.brand { display: flex; align-items: center; gap: 11px; }
.brand .mark { width: 11px; height: 11px; border-radius: 50%; background: var(--green); box-shadow: 0 0 12px var(--green); }
.brand .wm { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 22px; font-weight: 700; letter-spacing: -.02em; }
.brand .g { color: var(--green); }
.pitchbody { flex: 1; display: flex; flex-direction: column; justify-content: center; max-width: 460px; }
.pitchbody h1 { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 40px; line-height: 1.08; font-weight: 700; letter-spacing: -.02em; }
.pitchbody h1 .g { color: var(--green); }
.tag { color: var(--txt-2); font-size: 15px; line-height: 1.55; margin-top: 16px; }
.feats { list-style: none; margin-top: 26px; display: flex; flex-direction: column; gap: 13px; }
.feats li { display: flex; align-items: flex-start; gap: 11px; font-size: 14px; color: var(--txt); }
.feats .ck { color: var(--green); font-weight: 800; }
.rg { color: var(--txt-3); font-size: 11.5px; }

/* form */
.formpane { display: flex; align-items: center; justify-content: center; padding: 40px 24px; }
.form { width: 100%; max-width: 360px; }
.brand.mob { display: none; margin-bottom: 22px; }
.form h2 { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 28px; font-weight: 700; letter-spacing: -.02em; }
.sub { color: var(--txt-2); font-size: 13.5px; margin: 8px 0 24px; line-height: 1.5; }
form { display: flex; flex-direction: column; gap: 15px; }
label { display: flex; flex-direction: column; gap: 7px; font-size: 12px; font-weight: 600; color: var(--txt-2); text-transform: uppercase; letter-spacing: .05em; }
input { background: var(--bg); border: 1px solid var(--hair); border-radius: 11px; padding: 13px 15px; color: var(--txt); font-size: 14px; font-family: inherit; font-weight: 400; text-transform: none; letter-spacing: normal; }
input::placeholder { color: var(--txt-3); }
input:focus { outline: none; border-color: var(--hair-2); }
.primary { background: var(--green); color: #04210f; border: none; font-weight: 800; font-size: 14px; padding: 14px; border-radius: 11px; cursor: pointer; text-transform: uppercase; letter-spacing: .4px; margin-top: 4px; }
.primary:disabled { opacity: .6; }
.err { color: #ff5a52; font-size: 12.5px; margin-top: 12px; }
.switch { color: var(--txt-2); font-size: 13.5px; margin-top: 20px; }
.switch a { color: var(--green); font-weight: 600; }

@media (max-width: 820px) {
  .auth { grid-template-columns: 1fr; }
  .pitch { display: none; }
  .formpane { padding: 32px 18px; align-items: flex-start; padding-top: 14vh; }
  .brand.mob { display: flex; }
}
</style>
