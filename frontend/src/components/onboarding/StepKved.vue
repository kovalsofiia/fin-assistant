<script setup>
import { ref, computed } from 'vue';
import { useOnboardingStore } from '@/stores/onboarding';
import { KVED_SECTIONS } from '@/constants/kveds';

const store = useOnboardingStore();
const searchQuery = ref('');
const openSections = ref({});

// Фільтрація списку з урахуванням ієрархії
const filteredKveds = computed(() => {
  if (!searchQuery.value) return KVED_SECTIONS;
  const lowerQuery = searchQuery.value.toLowerCase();
  
  return KVED_SECTIONS.map(section => ({
    ...section,
    groups: section.groups.map(g => ({
      ...g,
      items: g.items.filter(kved => 
        kved.code.includes(lowerQuery) || 
        kved.name.toLowerCase().includes(lowerQuery)
      )
    })).filter(g => g.items.length > 0)
  })).filter(s => s.groups.length > 0);
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

const toggleSection = (id) => {
  openSections.value[id] = !openSections.value[id];
};

// Функція для підсвічування частин тексту, що збігаються з пошуком
const highlightMatch = (text, query) => {
  if (!query) return text;
  const parts = text.split(new RegExp(`(${query})`, 'gi'));
  return parts.map(part => 
    part.toLowerCase() === query.toLowerCase() 
      ? `<span class="bg-yellow-100 text-yellow-800 rounded px-0.5 font-bold">${part}</span>` 
      : part
  ).join('');
};

const clearSearch = () => {
  searchQuery.value = '';
};
</script>

<template>
  <div class="step-kved">
    <h2 class="text-xl font-bold mb-2">Виберіть види діяльності (КВЕД)</h2>
    <p class="text-gray-500 mb-6">Це допоможе визначити дозволену групу оподаткування.</p>

    <div class="search-box mb-6 relative group">
      <input 
        type="text" 
        v-model="searchQuery" 
        placeholder="Пошук за назвою або кодом (напр. IT, 62.01)..." 
        class="search-input w-full px-6 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800 shadow-sm"
      />
      <button 
        v-if="searchQuery" 
        @click="clearSearch"
        class="absolute right-4 top-1/2 -translate-y-1/2 p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
      >
        ×
      </button>
    </div>

    <div v-if="store.userData.selectedKveds.length > 0" class="selected-chips flex flex-wrap gap-2 mb-4">
      <div v-for="kved in store.userData.selectedKveds" :key="kved.code" class="chip bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm flex items-center gap-2">
        <span>{{ kved.code }}</span>
        <button @click="toggleKved(kved)" class="remove-btn font-bold">×</button>
      </div>
    </div>

    <div class="kved-list-container h-[350px] overflow-y-auto border rounded-xl divide-y">
      <div v-for="section in filteredKveds" :key="section.id" class="section">
        <button 
          @click="toggleSection(section.id)"
          class="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 text-left transition-colors"
        >
          <span class="font-bold text-sm text-gray-700">{{ section.title }}</span>
          <span class="text-xs text-gray-400">{{ openSections[section.id] ? '▲' : '▼' }}</span>
        </button>

        <div v-if="openSections[section.id] || searchQuery" class="groups divide-y bg-white">
          <div v-for="group in section.groups" :key="group.id" class="group-inner">
            <div class="px-4 py-2 bg-gray-50/50 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              {{ group.title }}
            </div>
            <div class="items divide-y divide-gray-50">
              <div 
                v-for="kved in group.items" 
                :key="kved.code" 
                class="kved-item flex items-center p-4 cursor-pointer hover:bg-blue-50 transition-colors"
                :class="{ 'bg-blue-50': isSelected(kved.code) }"
                @click="toggleKved(kved)"
              >
                <div class="checkbox w-5 h-5 border-2 rounded mr-4 flex items-center justify-center transition-colors"
                  :class="isSelected(kved.code) ? 'bg-blue-600 border-blue-600' : 'border-gray-300'"
                >
                  <span v-if="isSelected(kved.code)" class="text-white text-xs">✓</span>
                </div>
                <div class="info flex-1">
                  <div class="flex items-start gap-2 py-0.5">
                    <span class="code font-mono font-black text-blue-600 whitespace-nowrap" v-html="highlightMatch(kved.code, searchQuery)"></span>
                    <span class="name text-sm text-gray-700 leading-snug" v-html="highlightMatch(kved.name, searchQuery)"></span>
                  </div>
                </div>
                <div class="group-badges flex gap-1">
                  <span v-for="g in kved.allowedGroups" :key="g" class="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded border text-gray-500">
                    {{ g }} гр.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="searchQuery && filteredKveds.length === 0" class="p-12 text-center">
        <div class="text-4xl mb-4 text-gray-300">🔍</div>
        <p class="font-black text-gray-500 uppercase tracking-widest text-sm">Нічого не знайдено</p>
        <p class="text-xs text-gray-400 mt-2 italic font-medium">Спробуйте змінити запит або код</p>
      </div>
    </div>

    <div class="actions flex justify-between mt-8">
      <button class="px-6 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium transition-colors" @click="store.prevStep">Назад</button>
      <button 
        class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold disabled:opacity-50 transition-colors" 
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