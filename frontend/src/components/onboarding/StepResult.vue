<script setup>
import { onMounted } from 'vue';
import { useOnboardingStore } from '@/stores/onboarding';
import { useRouter } from 'vue-router';

const store = useOnboardingStore();
const router = useRouter();

onMounted(() => {
  store.calculateRecommendation();
});

const handleFinish = async () => {
  try {
    await store.submitOnboarding(); // Викликаємо нову функцію стору
    router.push('/settings');
  } catch (e) {
    alert("Помилка збереження даних");
  }
};
</script>

<template>
  <div class="result-step">
    <h2>Ваш профіль налаштовано!</h2>
    <div class="recommendation-card">
      <p class="label">Рекомендована група ФОП:</p>
      <div class="group-number">{{ store.userData.recommendedGroup }} ГРУПА</div>
    </div>

    <div class="actions">
      <button class="btn-secondary" @click="store.prevStep">Назад</button>
      <button class="btn-primary" @click="handleFinish" :disabled="store.isLoading">
        {{ store.isLoading ? 'Збереження...' : 'Почати роботу' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.result-step { text-align: center; }
.subtitle { color: #666; margin-bottom: 20px; }

.recommendation-summary {
  background: #e8f5e9;
  border: 1px solid #4CAF50;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 25px;
  color: #2e7d32;
}

.auth-form {
  background: white;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 12px;
  text-align: left;
  margin-bottom: 25px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.03);
}

.form-group { margin-bottom: 15px; }
.form-group label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 0.9em; color: #444; }
input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; }

.error-msg { color: red; font-size: 0.9em; margin-top: 10px; }

.actions { display: flex; justify-content: space-between; }
.btn-primary { background: #4CAF50; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 1.1em; font-weight: bold; width: 60%; }
.btn-secondary { background: #eee; color: #333; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; width: 35%; }
.btn-primary:disabled { background: #a5d6a7; cursor: wait; }
</style>