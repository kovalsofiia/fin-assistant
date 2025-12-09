<script setup>
import { ref } from 'vue'
import { supabase } from './supabase'

const email = ref('')
const password = ref('')
const loading = ref(false)
const message = ref('')

const handleSignUp = async () => {
  try {
    loading.value = true
    message.value = 'Реєстрація...'
    
    const { data, error } = await supabase.auth.signUp({
      email: email.value,
      password: password.value,
      options: {
        data: {
          full_name: 'Тестовий ФОП', // Це піде в таблицю profiles
        },
      },
    })

    if (error) throw error
    message.value = 'Успіх! Користувача створено.'
    console.log(data)
  } catch (error) {
    message.value = `Помилка: ${error.message}`
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container">
    <h1>Перевірка зв'язку 🛰️</h1>
    <div class="card">
      <input v-model="email" type="email" placeholder="Email" />
      <input v-model="password" type="password" placeholder="Пароль" />
      <button @click="handleSignUp" :disabled="loading">
        {{ loading ? 'Обробка...' : 'Зареєструватися' }}
      </button>
      <p class="message">{{ message }}</p>
    </div>
  </div>
</template>

<style scoped>
.container { display: flex; flex-direction: column; align-items: center; padding-top: 50px; font-family: sans-serif; }
.card { display: flex; flex-direction: column; gap: 10px; width: 300px; }
input { padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
button { padding: 10px; background-color: #42b883; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; }
button:disabled { background-color: #ccc; }
.message { text-align: center; margin-top: 10px; }
</style>