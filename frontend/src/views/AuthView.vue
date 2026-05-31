<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <h1 class="brand">Parlay<span>Pal</span> <em>Signals</em></h1>
      <p class="lead">{{ mode === 'login' ? 'Welcome back.' : 'Create your account to see live value bets.' }}</p>

      <form @submit.prevent="submit">
        <input v-model="email" type="email" placeholder="you@email.com" autocomplete="email" required />
        <input v-model="password" type="password" placeholder="Password (8+ characters)" autocomplete="current-password" required />
        <button class="primary" :disabled="loading" type="submit">
          {{ loading ? '…' : (mode === 'login' ? 'Log in' : 'Sign up free') }}
        </button>
      </form>

      <p v-if="error" class="err">{{ error }}</p>

      <p class="switch">
        {{ mode === 'login' ? "No account?" : 'Already have one?' }}
        <a href="#" @click.prevent="toggle">{{ mode === 'login' ? 'Sign up' : 'Log in' }}</a>
      </p>

      <p class="rg">21+. For entertainment, not financial advice. 1-800-GAMBLER.</p>
    </div>
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
.auth-wrap { min-height: 70vh; display: flex; align-items: center; justify-content: center; padding: 24px 14px;
  background: radial-gradient(circle at 50% 0%, #0e1618, #05080a 60%); }
.auth-card { width: 100%; max-width: 360px; background: #13191b; border: 1px solid #222d30; border-radius: 18px; padding: 26px 22px; }
.brand { font-family: 'Archivo Narrow', sans-serif; text-transform: uppercase; letter-spacing: 1px; font-size: 22px; color: #eef3f2; }
.brand span { color: #1fd65f; }
.brand em { font-style: normal; color: #8a9a9c; font-size: 14px; }
.lead { color: #8a9a9c; font-size: 13px; margin: 8px 0 18px; }
form { display: flex; flex-direction: column; gap: 10px; }
input { background: #0a0e0f; border: 1px solid #222d30; border-radius: 10px; padding: 12px 14px; color: #eef3f2; font-size: 14px; }
input::placeholder { color: #5f6f71; }
.primary { background: #1fd65f; color: #04210f; border: none; font-weight: 800; font-size: 14px; padding: 12px; border-radius: 10px; cursor: pointer; text-transform: uppercase; letter-spacing: .4px; }
.primary:disabled { opacity: .6; }
.err { color: #ff5a52; font-size: 12.5px; margin-top: 10px; }
.switch { color: #8a9a9c; font-size: 13px; margin-top: 16px; }
.switch a { color: #1fd65f; }
.rg { color: #5f6f71; font-size: 10.5px; margin-top: 18px; line-height: 1.5; }
</style>
