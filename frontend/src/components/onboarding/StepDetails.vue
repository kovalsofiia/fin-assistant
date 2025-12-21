<script setup>
import { Check } from 'lucide-vue-next';
import { useOnboardingStore } from '@/stores/onboarding';
const store = useOnboardingStore();
</script>

<template>
  <div class="step-details">
    <h2>Деталі діяльності</h2>
    <p class="subtitle">Це допоможе визначити оптимальну групу оподаткування.</p>
    
    <div class="form-group checkbox-group">
      <label class="checkbox-label" :class="{ active: store.userData.hasZed }">
        <div class="relative w-6 h-6 shrink-0">
          <input type="checkbox" v-model="store.userData.hasZed" class="peer appearance-none w-6 h-6 border-2 border-gray-200 checked:bg-green-600 checked:border-green-600 rounded-lg transition-all" />
          <div class="absolute inset-0 flex items-center justify-center text-white opacity-0 peer-checked:opacity-100 pointer-events-none">
            <Check :size="14" stroke-width="4" />
          </div>
        </div>
        <span class="text">
          <strong>Маю валютні надходження (ЗЕД)</strong>
          <br><small>Робота з іноземними замовниками (Upwork, прямі контракти, Google AdSense тощо)</small>
        </span>
      </label>
    </div>

    <div class="form-group">
      <label>Орієнтовний річний дохід (грн)</label>
      <input 
        type="number" 
        v-model="store.userData.annualIncome" 
        placeholder="Наприклад: 1000000" 
        min="0"
      />
    </div>
    
    <div class="form-group">
      <label>Кількість найманих працівників</label>
      <input 
        type="number" 
        v-model="store.userData.employeesCount" 
        min="0" 
        placeholder="0"
      />
    </div>

    <div class="actions">
      <button class="btn-secondary" @click="store.prevStep">Назад</button>
      <button class="btn-primary" @click="store.nextStep">Далі</button>
    </div>
  </div>
</template>

<style scoped>
.step-details { max-width: 100%; }
.subtitle { color: #666; margin-bottom: 20px; }
.form-group { margin-bottom: 25px; }

/* Стилі для чекбокса */
.checkbox-label { 
  display: flex; 
  align-items: flex-start; 
  gap: 12px; 
  cursor: pointer; 
  border: 2px solid #eee; 
  padding: 15px; 
  border-radius: 8px; 
  transition: all 0.2s;
}
.checkbox-label:hover { border-color: #ccc; }
.checkbox-label.active { 
  border-color: #4CAF50; 
  background: #f9fff9; 
}
input[type="checkbox"] { margin-top: 5px; transform: scale(1.2); accent-color: #4CAF50; }

input[type="number"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; margin-top: 5px; }
input[type="number"]:focus { border-color: #4CAF50; outline: none; }

.actions { display: flex; justify-content: space-between; margin-top: 30px; }
.btn-secondary { background: #eee; color: #333; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; }
.btn-primary { background: #4CAF50; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; }
.btn-primary:hover { background: #45a049; }
</style>