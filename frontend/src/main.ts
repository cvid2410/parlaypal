import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createHead } from '@vueuse/head'
import router from './router'
import App from './App.vue'
import { i18n } from './i18n'
import { useAuthStore } from './stores/auth'
import './assets/main.css'

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {})
}

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(createHead())
app.use(i18n)
app.use(router)

// Hydrate auth (validate stored token / load tier) before mount so guards see it.
useAuthStore(pinia).fetchMe().finally(() => app.mount('#app'))
