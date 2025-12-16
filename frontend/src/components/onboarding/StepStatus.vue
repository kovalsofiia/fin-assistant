<script setup>
import { useOnboardingStore } from '@/stores/onboarding';
import { useRouter } from 'vue-router';

const store = useOnboardingStore();
const router = useRouter();

const selectStatus = (isFop) => {
  store.userData.isFop = isFop;
};

const handleNext = async () => {
  // ЛОГІКА ПРОПУСКУ
  if (store.userData.isFop === false) {
    // Якщо користувач сказав "Я не ФОП" -> зберігаємо це і виходимо в налаштування
    try {
      await store.submitOnboarding();
      router.push('/settings');
    } catch (e) {
      console.error("Помилка збереження:", e);
    }
  } else {
    // Якщо ФОП -> йдемо по візарду далі
    store.nextStep();
  }
};
</script>

<template>
  <div class="step-status">
    <h2>Вітаємо у FOP Assistant! 🇺🇦</h2>
    <p class="subtitle">Давайте налаштуємо ваш профіль.</p>

    <div class="options-grid">
      <div 
        class="card-option" 
        :class="{ active: store.userData.isFop === true }"
        @click="selectStatus(true)"
      >
        <span class="icon">💼</span>
        <h3>Я вже ФОП</h3>
        <p>Веду діяльність та маю відкритий ФОП</p>
      </div>

      <div 
        class="card-option"
        :class="{ active: store.userData.isFop === false }"
        @click="selectStatus(false)"
      >
        <span class="icon">🚀</span>
        <h3>Тільки планую (Не ФОП)</h3>
        <p>Хочу вести облік особистих фінансів або планую відкриття</p>
      </div>
    </div>

    <div class="actions">
      <button class="btn-primary" @click="handleNext">Продовжити</button>
    </div>
  </div>
</template>

<style scoped>
.subtitle { color: #666; margin-bottom: 20px; }
.options-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
.card-option { border: 2px solid #eee; padding: 20px; border-radius: 10px; cursor: pointer; transition: all 0.2s; text-align: center; }
.card-option:hover { border-color: #4CAF50; background: #f9fff9; }
.card-option.active { border-color: #4CAF50; background: #e8f5e9; box-shadow: 0 0 0 4px rgba(76, 175, 80, 0.2); }
.icon { font-size: 2em; display: block; margin-bottom: 10px; }
.actions { text-align: right; }
.btn-primary { background: #4CAF50; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 16px; cursor: pointer; }
.btn-primary:hover { background: #45a049; }
</style>