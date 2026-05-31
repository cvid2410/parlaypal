import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', redirect: '/signals' },
    { path: '/scores', name: 'scores', component: () => import('../views/ScoresView.vue'), meta: { requiresAuth: true } },
    { path: '/signals', name: 'signals', component: () => import('../views/SignalsView.vue'), meta: { requiresAuth: true } },
    { path: '/ask', name: 'ask', component: () => import('../views/AskView.vue'), meta: { requiresAuth: true } },
    { path: '/results', name: 'results', component: () => import('../views/ResultsView.vue'), meta: { requiresAuth: true } },
    { path: '/leagues', name: 'leagues', component: () => import('../views/LeaguesView.vue'), meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: () => import('../views/AuthView.vue') },
    { path: '/privacy', name: 'privacy', component: () => import('../views/PrivacyView.vue') },
    { path: '/terms', name: 'terms', component: () => import('../views/TermsView.vue') },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth) {
    const auth = useAuthStore()
    if (!auth.isAuthed) return { name: 'login' }
  }
})

export default router
