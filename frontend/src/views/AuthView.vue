<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { supabase } from '@/supabase';
import api from '@/api';

const router = useRouter();
const isLoginMode = ref(true); // Перемикач Вхід / Реєстрація
const email = ref('');
const password = ref('');
const fullName = ref('');
const isLoading = ref(false);
const errorMsg = ref('');

const handleAuth = async () => {
  isLoading.value = true;
  errorMsg.value = '';

  try {
    if (isLoginMode.value) {
      // --- ЛОГІКА ВХОДУ ---
      const { error } = await supabase.auth.signInWithPassword({
        email: email.value,
        password: password.value
      });
      if (error) throw error;
      
      // Успішний вхід -> йдемо в Налаштування (або Dashboard)
      router.push('/settings');

    } else {
      // --- ЛОГІКА РЕЄСТРАЦІЇ ---
      const { data, error } = await supabase.auth.signUp({
        email: email.value,
        password: password.value,
        options: { data: { full_name: fullName.value } }
      });
      
      if (error) throw error;
      if (!data.user) throw new Error("Не вдалося створити користувача");

      // 1. Створюємо "пустий" профіль у базі
      // За замовчуванням is_fop = false (змінимо це на онбордингу)
      await api.createProfile({
        user_id: data.user.id,
        is_fop: false, 
        full_name: fullName.value
      });

      // 2. Нового юзера ведемо на Онбординг
      router.push('/onboarding');
    }
  } catch (e) {
    console.error(e);
    errorMsg.value = e.message || "Помилка авторизації";
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="auth-container">
    <div class="auth-card">
      <h1>{{ isLoginMode ? 'Вхід' : 'Реєстрація' }}</h1>
      <p class="subtitle">FOP Assistant</p>

      <form @submit.prevent="handleAuth">
        
        <div v-if="!isLoginMode" class="form-group">
          <label>Ваше ім'я</label>
          <input type="text" v-model="fullName" required placeholder="Тарас" />
        </div>

        <div class="form-group">
          <label>Email</label>
          <input type="email" v-model="email" required placeholder="email@example.com" />
        </div>

        <div class="form-group">
          <label>Пароль</label>
          <input type="password" v-model="password" required placeholder="********" minlength="6" />
        </div>

        <div v-if="errorMsg" class="error">{{ errorMsg }}</div>

        <button type="submit" :disabled="isLoading" class="btn-primary">
          {{ isLoading ? 'Зачекайте...' : (isLoginMode ? 'Увійти' : 'Зареєструватися') }}
        </button>
      </form>

      <p class="toggle-text">
        {{ isLoginMode ? "Ще не маєте акаунту?" : "Вже зареєстровані?" }}
        <span @click="isLoginMode = !isLoginMode" class="link">
          {{ isLoginMode ? "Створити акаунт" : "Увійти" }}
        </span>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f2f5; }
.auth-card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }
.form-group { margin-bottom: 1rem; text-align: left; }
.form-group label { display: block; margin-bottom: 0.5rem; font-weight: bold; font-size: 0.9rem; }
input { width: 100%; padding: 0.75rem; border: 1px solid #ccc; border-radius: 6px; }
.btn-primary { width: 100%; padding: 0.75rem; background: #4CAF50; color: white; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; margin-top: 1rem; }
.btn-primary:disabled { background: #a5d6a7; }
.error { color: red; margin-top: 10px; font-size: 0.9rem; }
.toggle-text { margin-top: 1.5rem; font-size: 0.9rem; }
.link { color: #4CAF50; cursor: pointer; font-weight: bold; }
.link:hover { text-decoration: underline; }
</style>