<script setup>
import { ref } from 'vue';
import { RouterView, useRouter, useRoute } from 'vue-router';
import { supabase } from '@/supabase';
import { 
  Wallet, 
  LayoutDashboard, 
  Receipt, 
  Settings, 
  Menu, 
  X, 
  LogOut 
} from 'lucide-vue-next';
import './assets/main.css'

const router = useRouter();
const route = useRoute();
const isMenuOpen = ref(false);

const handleLogout = async () => {
  await supabase.auth.signOut();
  router.push('/');
};

const navigation = [
  { name: 'Дашборд', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Транзакції', path: '/transactions', icon: Receipt },
  { name: 'Налаштування', path: '/settings', icon: Settings },
];

const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value;
};
</script>

<template>
  <div class="app-layout min-h-screen bg-gray-50 flex flex-col font-sans">
    <!-- Navigation Bar -->
    <header 
      v-if="!['/', '/onboarding'].includes($route.path)" 
      class="bg-white border-b border-gray-200 sticky top-0 z-50 transition-all duration-300"
    >
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <!-- Logo Section -->
          <div class="flex items-center">
            <div class="flex-shrink-0 flex items-center gap-3 group cursor-pointer" @click="router.push('/dashboard')">
              <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-200 group-hover:scale-105 transition-transform">
                <Wallet :size="20" />
              </div>
              <span class="text-xl font-extrabold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                FOP Assistant
              </span>
            </div>
            
            <!-- Desktop Navigation -->
            <nav class="hidden md:ml-10 md:flex md:space-x-1">
              <RouterLink 
                v-for="item in navigation" 
                :key="item.path"
                :to="item.path"
                class="inline-flex items-center px-4 py-2 text-sm font-semibold rounded-xl transition-all duration-200"
                :class="route.path === item.path 
                  ? 'bg-blue-50 text-blue-700 shadow-sm' 
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'"
              >
                <component :is="item.icon" :size="18" class="mr-2" />
                {{ item.name }}
              </RouterLink>
            </nav>
          </div>

          <!-- User Actions -->
          <div class="hidden md:flex items-center gap-4">
            <button 
              @click="handleLogout"
              class="flex items-center gap-2 px-4 py-2 text-sm font-bold text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"
            >
              <LogOut :size="18" />
              Вихід
            </button>
          </div>

          <!-- Mobile menu button -->
          <div class="flex md:hidden items-center">
            <button 
              @click="toggleMenu"
              class="inline-flex items-center justify-center p-2 rounded-xl text-gray-400 hover:text-gray-600 hover:bg-gray-100 focus:outline-none transition-colors"
            >
              <Menu v-if="!isMenuOpen" :size="24" />
              <X v-else :size="24" />
            </button>
          </div>
        </div>
      </div>

      <!-- Mobile menu -->
      <transition 
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 -translate-y-4"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-4"
      >
        <div v-show="isMenuOpen" class="md:hidden bg-white border-t border-gray-100 shadow-xl rounded-b-2xl mx-2 mt-1">
          <div class="px-2 pt-2 pb-3 space-y-1">
            <RouterLink 
              v-for="item in navigation" 
              :key="item.path"
              :to="item.path"
              @click="isMenuOpen = false"
              class="block px-4 py-4 text-base font-bold rounded-xl transition-colors"
              :class="route.path === item.path 
                ? 'bg-blue-50 text-blue-700' 
                : 'text-gray-600 hover:bg-gray-50'"
            >
              <div class="flex items-center gap-4">
                <component :is="item.icon" :size="20" />
                {{ item.name }}
              </div>
            </RouterLink>
            <div class="h-px bg-gray-100 my-2 mx-4"></div>
            <button 
              @click="handleLogout"
              class="w-full text-left px-4 py-4 text-base font-bold text-red-600 hover:bg-red-50 rounded-xl flex items-center gap-4 transition-colors"
            >
              <LogOut :size="20" />
              Вийти з акаунту
            </button>
          </div>
        </div>
      </transition>
    </header>

    <main class="flex-grow">
      <RouterView />
    </main>
  </div>
</template>

<style>
/* Ensure body doesn't have extra padding if layout already handles it */
body {
  margin: 0;
  padding: 0;
}
</style>