<script setup>
import { RouterView } from 'vue-router';
</script>

<template>
  <div class="app-layout">
    <header v-if="$route.path !== '/onboarding'" class="main-header">
       <nav>
         <RouterLink to="/settings">Налаштування</RouterLink>
         </nav>
    </header>

    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
/* Глобальні стилі для контейнера */
.app-layout {
  font-family: Arial, sans-serif;
  min-height: 100vh;
  background-color: #f5f7fa; /* Світло-сірий фон для всього додатку */
}

.main-header {
  background: white;
  padding: 15px 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  margin-bottom: 20px;
}

nav a {
  text-decoration: none;
  color: #333;
  font-weight: bold;
  margin-right: 15px;
}

nav a.router-link-active {
  color: #4CAF50;
}
</style>