<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { supabase } from '@/supabase';
import api from '@/api';
import { Wallet, AlertCircle, Loader2 } from 'lucide-vue-next';

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
      const { error } = await supabase.auth.signInWithPassword({
        email: email.value,
        password: password.value
      });
      if (error) throw error;
      router.push('/dashboard');
    } else {
      const { data, error } = await supabase.auth.signUp({
        email: email.value,
        password: password.value,
        options: { data: { full_name: fullName.value } }
      });
      
      if (error) throw error;
      if (!data.user) throw new Error("Не вдалося створити користувача");

      try {
        await api.createProfile({
          user_id: data.user.id,
          is_fop: false, 
          full_name: fullName.value
        });
      } catch (profileError) {
        console.error("Profile creation error:", profileError);
      }

      router.push('/onboarding');
    }
  } catch (e) {
    console.error(e);
    errorMsg.value = e.message === "Invalid login credentials" 
      ? "Невірний email або пароль" 
      : (e.message || "Помилка авторизації");
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-0 sm:p-4 bg-gray-50 font-sans">
    <div class="max-w-md w-full bg-white sm:rounded-3xl shadow-2xl p-8 sm:p-12 animate-slide-up border border-gray-100 min-h-screen sm:min-h-0 flex flex-col justify-center">
      <!-- Logo Section -->
      <div class="flex flex-col items-center mb-10">
        <div class="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-blue-200 mb-6 animate-bounce-slow">
          <Wallet :size="32" stroke-width="2.5" />
        </div>
        <h1 class="text-3xl font-black text-gray-900 tracking-tight">FOP Assistant</h1>
        <p class="text-gray-500 font-medium mt-2">
          {{ isLoginMode ? 'Вхід в особистий кабінет' : 'Створіть свій профіль' }}
        </p>
      </div>

      <form @submit.prevent="handleAuth" class="space-y-6">
        <!-- Name Field (Registration only) -->
        <div v-if="!isLoginMode" class="space-y-1">
          <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Ваше ім'я</label>
          <input 
            type="text" 
            v-model="fullName" 
            required 
            placeholder="Тарас Шевченко" 
            class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800 placeholder:text-gray-300"
          />
        </div>

        <div class="space-y-1">
          <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Email</label>
          <input 
            type="email" 
            v-model="email" 
            required 
            placeholder="email@example.com" 
            class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800 placeholder:text-gray-300"
          />
        </div>

        <div class="space-y-1">
          <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Пароль</label>
          <input 
            type="password" 
            v-model="password" 
            required 
            placeholder="********" 
            minlength="6" 
            class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800 placeholder:text-gray-300"
          />
        </div>

        <!-- Error Block -->
        <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
          <div v-if="errorMsg" class="p-4 bg-red-50 text-red-700 text-sm font-bold rounded-2xl flex items-center gap-3 border border-red-100">
            <AlertCircle :size="18" stroke-width="3" /> 
            <span>{{ errorMsg }}</span>
          </div>
        </transition>

        <!-- Action Button -->
        <button 
          type="submit" 
          :disabled="isLoading" 
          class="w-full py-5 rounded-2xl font-black bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-3 transition-all shadow-xl shadow-blue-200 active:scale-[0.98] mt-4"
        >
          <Loader2 v-if="isLoading" class="animate-spin" :size="20" />
          {{ isLoading ? 'Завантаження...' : (isLoginMode ? 'Увійти' : 'Зареєструватися') }}
        </button>
      </form>

      <!-- Toggle Mode -->
      <div class="mt-10 text-center border-t border-gray-100 pt-8">
        <p class="text-gray-500 font-medium">
          {{ isLoginMode ? "Ще не маєте акаунту?" : "Вже зареєстровані?" }}
          <button 
            @click="isLoginMode = !isLoginMode; errorMsg = ''" 
            class="text-blue-600 font-black hover:text-blue-800 transition-colors ml-2 focus:outline-none underline underline-offset-4 decoration-2 decoration-blue-100 hover:decoration-blue-600"
          >
            {{ isLoginMode ? "Зареєструватися" : "Увійти" }}
          </button>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-slide-up { animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

.animate-bounce-slow { animation: bounceSlow 3s infinite; }
@keyframes bounceSlow { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }

.loader {
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    border-top: 2px solid #ffffff;
    width: 20px;
    height: 20px;
    animation: spin 0.8s linear infinite;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>