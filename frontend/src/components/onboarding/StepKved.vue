<script setup>
import { ref, computed } from 'vue';
import { useOnboardingStore } from '@/stores/onboarding';
import kvedsData from '@/assets/data/kveds.json';

const store = useOnboardingStore();
const searchQuery = ref('');

// Фільтрація списку
const filteredKveds = computed(() => {
  if (!searchQuery.value) return kvedsData;
  const lowerQuery = searchQuery.value.toLowerCase();
  return kvedsData.filter(kved => 
    kved.code.includes(lowerQuery) || 
    kved.name.toLowerCase().includes(lowerQuery)
  );
});

// Додавання/видалення КВЕДу
const toggleKved = (kved) => {
  const index = store.userData.selectedKveds.findIndex(k => k.code === kved.code);
  if (index === -1) {
    store.userData.selectedKveds.push(kved);
  } else {
    store.userData.selectedKveds.splice(index, 1);
  }
};

const isSelected = (code) => {
  return store.userData.selectedKveds.some(k => k.code === code);
};
</script>

<template>
  <div class="step-kved">
    <h2>Виберіть види діяльності (КВЕД)</h2>
    <p class="subtitle">Це допоможе визначити дозволену групу оподаткування.</p>

    <div class="search-box">
      <input 
        type="text" 
        v-model="searchQuery" 
        placeholder="Пошук за назвою або кодом (напр. IT, 62.01)..." 
        class="search-input"
      />
    </div>

    <div v-if="store.userData.selectedKveds.length > 0" class="selected-chips">
      <div v-for="kved in store.userData.selectedKveds" :key="kved.code" class="chip">
        <span>{{ kved.code }}</span>
        <button @click="toggleKved(kved)" class="remove-btn">×</button>
      </div>
    </div>

    <div class="kved-list">
      <div 
        v-for="kved in filteredKveds" 
        :key="kved.code" 
        class="kved-item"
        :class="{ active: isSelected(kved.code) }"
        @click="toggleKved(kved)"
      >
        <div class="checkbox">
          <div class="check-mark" v-if="isSelected(kved.code)">✓</div>
        </div>
        <div class="info">
          <span class="code">{{ kved.code }}</span>
          <span class="name">{{ kved.name }}</span>
        </div>
        <div class="group-badge">{{ kved.group }}</div>
      </div>
    </div>

    <div class="actions">
      <button class="btn-secondary" @click="store.prevStep">Назад</button>
      <button 
        class="btn-primary" 
        @click="store.nextStep"
        :disabled="store.userData.selectedKveds.length === 0"
      >
        Далі
      </button>
    </div>
  </div>
</template>

<style scoped>
.search-input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 15px; font-size: 16px; }
.kved-list { max-height: 300px; overflow-y: auto; border: 1px solid #eee; border-radius: 8px; }
.kved-item { display: flex; align-items: center; padding: 12px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; }
.kved-item:hover { background: #f9f9f9; }
.kved-item.active { background: #e8f5e9; }

.checkbox { width: 20px; height: 20px; border: 2px solid #ddd; border-radius: 4px; margin-right: 12px; display: flex; align-items: center; justify-content: center; background: white; }
.kved-item.active .checkbox { border-color: #4CAF50; background: #4CAF50; color: white; }

.info { flex: 1; display: flex; flex-direction: column; }
.code { font-weight: bold; color: #333; font-size: 0.9em; }
.name { color: #555; font-size: 0.9em; }
.group-badge { background: #eee; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; color: #666; }

.selected-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px; }
.chip { background: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 16px; font-size: 0.9em; display: flex; align-items: center; gap: 6px; }
.remove-btn { border: none; background: none; color: inherit; cursor: pointer; font-weight: bold; font-size: 1.1em; }

.actions { display: flex; justify-content: space-between; margin-top: 20px; }
.btn-primary { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; }
.btn-primary:disabled { background: #ccc; cursor: not-allowed; }
.btn-secondary { background: #eee; color: #333; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; }
</style>