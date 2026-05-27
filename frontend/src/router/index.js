import { createRouter, createWebHistory } from 'vue-router';
import { supabase } from '@/services/supabase'; // Для перевірки сесії

import AuthView from '@/views/AuthView.vue';
import OnboardingView from '@/views/OnboardingView.vue';
import SettingsView from '@/views/SettingsView.vue';
import DashboardView from '@/views/DashboardView.vue';
import AnalyticsView from '@/views/AnalyticsView.vue';
import FopGroupQuizView from '@/views/FopGroupQuizView.vue';
import AdminTaxRulesView from '@/views/AdminTaxRulesView.vue';
import AdminQuizRulesView from '@/views/AdminQuizRulesView.vue';

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
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true }
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: AnalyticsView,
      meta: { requiresAuth: true }
    },
    {
      path: '/quiz/fop-group',
      name: 'fop-group-quiz',
      component: FopGroupQuizView,
      meta: { requiresAuth: true }
    },
    {
      path: '/admin/tax-rules',
      name: 'admin-tax-rules',
      component: AdminTaxRulesView,
      meta: { requiresAuth: true }
    },
    {
      path: '/admin/quiz-rules',
      name: 'admin-quiz-rules',
      component: AdminQuizRulesView,
      meta: { requiresAuth: true }
    },
    {
      path: '/transactions',
      redirect: '/analytics'
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