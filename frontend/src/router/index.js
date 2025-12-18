import { createRouter, createWebHistory } from 'vue-router';
import { supabase } from '@/supabase'; // Для перевірки сесії

import AuthView from '@/views/AuthView.vue';
import OnboardingView from '@/views/OnboardingView.vue';
import SettingsView from '@/views/SettingsView.vue';
import DashboardView from '@/views/DashboardView.vue';
import TransactionsView from '@/views/TransactionsView.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'auth',
      component: AuthView
    },
    {
      path: '/onboarding',
      name: 'onboarding',
      component: OnboardingView,
      meta: { requiresAuth: true }
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true }
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: TransactionsView,
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true }
    }
  ]
});

router.beforeEach(async (to, from, next) => {
  const { data: { session } } = await supabase.auth.getSession();

  if (to.meta.requiresAuth && !session) {
    next('/');
  } 
  else if (to.path === '/' && session) {
    // Якщо залогінений - ведемо на Дашборд
    next('/dashboard');
  } 
  else {
    next();
  }
});

export default router;