import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const API = '/api'
const TOKEN_KEY = 'pp_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const tier = ref<string>('free')
  const email = ref<string>('')
  const ready = ref(false)

  const isAuthed = computed(() => !!token.value)
  const isPaid = computed(() => tier.value === 'bettor' || tier.value === 'sharp')

  function setToken(t: string | null) {
    token.value = t
    if (t) localStorage.setItem(TOKEN_KEY, t)
    else localStorage.removeItem(TOKEN_KEY)
  }

  async function authFetch(path: string, opts: RequestInit = {}) {
    const headers: Record<string, string> = { ...(opts.headers as any) }
    if (token.value) headers['Authorization'] = `Bearer ${token.value}`
    if (opts.body) headers['Content-Type'] = 'application/json'
    return fetch(API + path, { ...opts, headers })
  }

  async function _auth(path: string, e: string, p: string) {
    const res = await authFetch(path, { method: 'POST', body: JSON.stringify({ email: e, password: p }) })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || 'Authentication failed')
    setToken(data.access_token)
    tier.value = data.tier
    email.value = e
    ready.value = true
  }

  const signup = (e: string, p: string) => _auth('/auth/signup', e, p)
  const login = (e: string, p: string) => _auth('/auth/login', e, p)

  async function fetchMe() {
    if (!token.value) { ready.value = true; return }
    const res = await authFetch('/auth/me')
    if (res.ok) {
      const d = await res.json()
      tier.value = d.tier
      email.value = d.email
    } else {
      setToken(null)
    }
    ready.value = true
  }

  function logout() {
    setToken(null)
    tier.value = 'free'
    email.value = ''
  }

  async function upgrade(t: string) {
    // Dev-only path; replaced by Stripe Checkout (task 3.1b).
    const res = await authFetch('/billing/dev-upgrade', { method: 'POST', body: JSON.stringify({ tier: t }) })
    if (res.ok) tier.value = (await res.json()).tier
    return res.ok
  }

  return { token, tier, email, ready, isAuthed, isPaid, authFetch, signup, login, fetchMe, logout, upgrade }
})
