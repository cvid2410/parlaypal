<template>
  <div class="auth">
    <!-- one centered split-card: pitch on the left half, form on the right half. Keeping them
         inside a single bounded shell (instead of two full-bleed page halves) is what makes
         the composition read as balanced. -->
    <div class="shell">
    <!-- pitch panel (desktop): show the product, don't just describe it -->
    <aside class="pitch">
      <div class="brand"><span class="mark" aria-hidden="true" /><span class="wm">Parlay<span class="g">Pal</span></span></div>

      <div class="pitchbody">
        <h1>{{ $t('auth.hero_pre') }}<span class="g">{{ $t('auth.hero_em') }}</span>.</h1>
        <p class="tag">{{ $t('auth.tag') }}</p>

        <SignalPreview class="preview" aria-hidden="true" />
      </div>

      <p class="rg">{{ $t('auth.rg') }}</p>
    </aside>

    <!-- form panel -->
    <main class="formpane">
      <div class="card">
        <h2>{{ mode === 'login' ? $t('auth.welcome') : $t('auth.create') }}</h2>
        <p class="sub">{{ mode === 'login' ? $t('auth.sub_login') : $t('auth.sub_signup') }}</p>

        <form @submit.prevent="submit">
          <label>{{ $t('auth.email') }}
            <input v-model="email" type="email" placeholder="you@email.com" autocomplete="email" required />
          </label>
          <label>{{ $t('auth.password') }}
            <input v-model="password" type="password" :placeholder="$t('auth.pw_placeholder')" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" required />
          </label>
          <button class="primary" :disabled="loading" type="submit">
            {{ loading ? '…' : (mode === 'login' ? $t('auth.login_btn') : $t('auth.signup_btn')) }}
          </button>
        </form>

        <p v-if="error" class="err">{{ error }}</p>

        <p class="switch">
          {{ mode === 'login' ? $t('auth.no_account') : $t('auth.have_account') }}
          <button type="button" class="link" @click="toggle">{{ mode === 'login' ? $t('auth.signup_link') : $t('auth.login_link') }}</button>
        </p>
      </div>

      <!-- mobile only: the desktop pitch panel is hidden under 820px, so surface its sample
           signal cards here, under the form - the product preview is the best pitch we have -->
      <SignalPreview class="mob-preview" aria-hidden="true" />

      <footer class="legal">
        <span class="mob-rg">{{ $t('auth.mob_rg') }}</span>
        <RouterLink to="/privacy">{{ $t('common.privacy') }}</RouterLink>
        <span class="sep" aria-hidden="true">·</span>
        <RouterLink to="/terms">{{ $t('common.terms') }}</RouterLink>
      </footer>
    </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import SignalPreview from '../components/SignalPreview.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
// Login is the default: returning users are the common case once someone has an account,
// and new visitors are one click away via "Sign up".
const mode = ref<'login' | 'signup'>('login')
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
/* the page centers one bounded shell; the shell holds both halves */
.auth { display: grid; place-items: center; min-height: 100vh; padding: 40px 28px; }
.shell { display: grid; grid-template-columns: 1.1fr 1fr; width: 100%; max-width: 1060px;
  border: 1px solid var(--hair); border-radius: 24px; overflow: hidden; background: var(--bg);
  box-shadow: 0 30px 90px rgba(0, 0, 0, .5); }

/* pitch */
.pitch { background: var(--panel); border-right: 1px solid var(--hair); padding: 36px 40px; display: flex; flex-direction: column; min-height: 620px;
  background-image: radial-gradient(circle at 18% 10%, rgba(31, 214, 95, .12), transparent 46%); }
.brand { display: flex; align-items: center; gap: 11px; }
.brand .mark { width: 11px; height: 11px; border-radius: 50%; background: var(--green); box-shadow: 0 0 12px var(--green); }
.brand .wm { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 22px; font-weight: 700; letter-spacing: -.02em; }
.brand .g { color: var(--green); }
.pitchbody { flex: 1; display: flex; flex-direction: column; justify-content: center; max-width: 470px; }
.pitchbody h1 { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 42px; line-height: 1.05; font-weight: 700; letter-spacing: -.02em; }
.pitchbody h1 .g { color: var(--green); }
.tag { color: var(--txt-2); font-size: 15px; line-height: 1.55; margin-top: 16px; }

/* product preview (SignalPreview component): the desktop copy lives in the pitch panel;
   .mob-preview is the copy under the form, shown only on mobile where the pitch is hidden. */
.preview { margin-top: 28px; }
.mob-preview { display: none; }

.rg { color: var(--txt-3); font-size: 11.5px; }

/* form */
.formpane { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 22px; padding: 40px 24px; }
.card { width: 100%; max-width: 392px; background: var(--panel); border: 1px solid var(--hair); border-radius: 20px; padding: 34px 32px; box-shadow: 0 18px 50px rgba(0, 0, 0, .4); }
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
  /* the shell dissolves on mobile: borderless single column, top-aligned */
  .auth { place-items: start stretch; padding: 0; min-height: 100svh; }
  .shell { grid-template-columns: 1fr; max-width: none; border: none; border-radius: 0; box-shadow: none; }

  /* The pitch becomes a compact intro header: logo -> headline -> tagline, right above the
     form. Its sample cards are hidden here (they reappear under the form as .mob-preview)
     and its RG line lives in the legal footer. */
  .pitch { padding: 36px 18px 0; min-height: 0; border-right: none; background: transparent; background-image: none; }
  .pitch .preview, .pitch .rg { display: none; }
  .pitchbody { max-width: none; margin-top: 24px; }
  .pitchbody h1 { font-size: 31px; }
  .tag { font-size: 13.5px; margin-top: 12px; }

  /* Column flex: justify-content is the VERTICAL axis. Top-align the card instead of
     centering it - centering on a tall phone screen left a huge dead zone above the form. */
  .formpane { justify-content: flex-start; padding: 24px 18px 28px; gap: 20px; }
  .card { max-width: none; padding: 30px 24px; }
  /* the intro above carries the logo, so the in-card one stays hidden */
  /* the pitch's sample signal cards reappear under the form */
  .mob-preview { display: block; width: 100%; }
  .legal { justify-content: center; }
  /* the pitch's 1-800-GAMBLER line is hidden here, so surface it in the footer */
  .legal .mob-rg { display: inline; }
}
</style>
