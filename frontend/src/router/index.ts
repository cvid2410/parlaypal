import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'schedule',
      component: () => import('../views/ScheduleView.vue'),
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

export default router
