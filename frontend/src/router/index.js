import { createRouter, createWebHistory } from 'vue-router';
import { supabase } from '@/supabase'; // Для перевірки сесії

import AuthView from '@/views/AuthView.vue';
import OnboardingView from '@/views/OnboardingView.vue';
import SettingsView from '@/views/SettingsView.vue';

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
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true }
    }
  ]
});

// Глобальна перевірка авторизації перед кожним переходом
router.beforeEach(async (to, from, next) => {
  const { data: { session } } = await supabase.auth.getSession();

  // Якщо маршрут вимагає Auth, а користувач не залогінений -> кидаємо на вхід
  if (to.meta.requiresAuth && !session) {
    next('/');
  } 
  // Якщо користувач вже залогінений і йде на сторінку входу -> кидаємо в налаштування
  else if (to.path === '/' && session) {
    next('/settings');
  } 
  else {
    next();
  }
});

export default router;