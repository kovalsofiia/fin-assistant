<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api'; // Перевірте шлях до вашого api.js
import { supabase } from '@/supabase'; // Імпортуємо Supabase, щоб дізнатись хто залогінений

const router = useRouter();
const isLoading = ref(false);
const message = ref('');
const currentUserId = ref(null); // Тут будемо зберігати реальний ID

// Стан профілю
const profile = ref({
  full_name: '',
  is_fop: true
});

// Стан налаштувань ФОП
const fopSettings = ref({
  fop_group: 3,
  is_zed: false,
  income_tax_percent: 5,
  esv_value: 1760,
  military_tax_percent: 1.5
});

// Завантаження даних
const loadData = async () => {
  isLoading.value = true;
  try {
    // 1. ОТРИМУЄМО ПОТОЧНОГО КОРИСТУВАЧА
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      // Якщо користувач не залогінений - кидаємо назад на онбординг (або логін)
      router.push('/onboarding');
      return;
    }

    currentUserId.value = user.id; // Зберігаємо реальний ID
    console.log("Завантажуємо налаштування для:", currentUserId.value);

    // 2. Отримуємо профіль з бекенду
    const profileRes = await api.getProfile(currentUserId.value);
    profile.value = profileRes.data;

    // 3. Якщо користувач ФОП - тягнемо деталі
    if (profile.value.is_fop) {
      const settingsRes = await api.getFopSettings(currentUserId.value);
      // Якщо налаштування існують - записуємо їх
      if (settingsRes.data) {
          fopSettings.value = settingsRes.data;
      }
    }
  } catch (error) {
    console.error("Помилка завантаження:", error);
    message.value = "Не вдалося завантажити дані. Спробуйте оновити сторінку.";
  } finally {
    isLoading.value = false;
  }
};

// Збереження змін
const saveChanges = async () => {
  if (!currentUserId.value) return;
  
  message.value = '';
  try {
    // 1. Оновлюємо профіль
    await api.updateProfile(currentUserId.value, {
      full_name: profile.value.full_name,
      is_fop: profile.value.is_fop
    });

    // 2. Якщо ФОП увімкнено - оновлюємо податкові налаштування
    if (profile.value.is_fop) {
      await api.updateFopSettings(currentUserId.value, {
        fop_group: fopSettings.value.fop_group,
        is_zed: fopSettings.value.is_zed,
        income_tax_percent: fopSettings.value.income_tax_percent,
        esv_value: fopSettings.value.esv_value,
        military_tax_percent: fopSettings.value.military_tax_percent
      });
    }

    message.value = "✅ Налаштування збережено!";
  } catch (error) {
    console.error(error);
    message.value = "❌ Помилка збереження.";
  }
};

// Слідкуємо за перемикачем is_fop
watch(() => profile.value.is_fop, async (newVal) => {
  if (newVal && currentUserId.value) {
    try {
        const res = await api.getFopSettings(currentUserId.value);
        if(res.data) fopSettings.value = res.data;
    } catch (e) {
        console.log("Налаштувань ще немає, заповніть форму");
    }
  }
});

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="settings-container">
    <h1>Налаштування</h1>
    <form @submit.prevent="saveChanges">
      <div class="section">
        <label>Ім'я:</label>
        <input v-model="profile.full_name" type="text" />
      </div>
      <div class="section">
        <label>
          <input type="checkbox" v-model="profile.is_fop" />
          Я ФОП
        </label>
      </div>
      <div v-if="profile.is_fop" class="fop-details">
        <h3>Податки</h3>
        <label>Група: 
          <select v-model.number="fopSettings.fop_group">
            <option :value="1">1</option>
            <option :value="2">2</option>
            <option :value="3">3</option>
          </select>
        </label>
      </div>
      <button type="submit">Зберегти</button>
      <p>{{ message }}</p>
    </form>
  </div>
</template>

<style scoped>
.settings-container { max-width: 600px; margin: 20px auto; padding: 20px; }
.section { margin-bottom: 15px; }
.fop-details { border: 1px solid #ddd; padding: 15px; margin-top: 10px; }
</style>