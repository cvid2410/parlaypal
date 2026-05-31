import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/',
      name: 'schedule',
      component: () => import('../views/ScheduleView.vue'),
    },
    {
      path: '/signals',
      name: 'signals',
      component: () => import('../views/SignalsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/AuthView.vue'),
    },
    {
      path: '/parlay',
      name: 'parlay',
      component: () => import('../views/ParlayView.vue'),
    },
    {
      path: '/match/:id',
      name: 'match',
      component: () => import('../views/MatchDetailView.vue'),
    },
    {
      path: '/standings',
      name: 'standings',
      component: () => import('../views/StandingsView.vue'),
    },
    {
      path: '/bracket',
      name: 'bracket',
      component: () => import('../views/BracketView.vue'),
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: () => import('../views/PrivacyView.vue'),
    },
    {
      path: '/terms',
      name: 'terms',
      component: () => import('../views/TermsView.vue'),
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth) {
    const auth = useAuthStore()
    if (!auth.isAuthed) return { name: 'login' }
  }
})

export default router
