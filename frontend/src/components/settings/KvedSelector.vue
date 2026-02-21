<script setup>
import { ref, computed } from 'vue';
import { Search, X, ChevronDown, ChevronRight, Check } from 'lucide-vue-next';
import BaseModal from '@/components/common/BaseModal.vue';
import { KVED_SECTIONS } from '@/constants/kveds';

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  userKveds: {
    type: Array,
    required: true
  }
});

const emit = defineEmits(['close', 'update:userKveds']);

const kvedSearch = ref('');
const openSections = ref({});

const filteredKveds = computed(() => {
  if (!kvedSearch.value) return KVED_SECTIONS;
  const search = kvedSearch.value.toLowerCase();
  return KVED_SECTIONS.map(section => ({
    ...section,
    groups: section.groups.map(g => ({
      ...g,
      items: g.items.filter(i => i.code.includes(search) || i.name.toLowerCase().includes(search))
    })).filter(g => g.items.length > 0)
  })).filter(s => s.groups.length > 0);
});

const highlightMatch = (text, query) => {
  if (!query) return text;
  const parts = text.split(new RegExp(`(${query})`, 'gi'));
  return parts.map(part => 
    part.toLowerCase() === query.toLowerCase() 
      ? `<span class="bg-yellow-100 text-yellow-800 rounded px-0.5 font-bold">${part}</span>` 
      : part
  ).join('');
};

const toggleSection = (id) => { openSections.value[id] = !openSections.value[id]; };
const isKvedSelected = (code) => props.userKveds.some(k => k.code === code);

const toggleKved = (item) => {
  const currentKveds = [...props.userKveds];
  const idx = currentKveds.findIndex(k => k.code === item.code);
  
  if (idx >= 0) {
    currentKveds.splice(idx, 1);
  } else {
    currentKveds.push(item);
  }
  
  emit('update:userKveds', currentKveds);
};
</script>

<template>
  <BaseModal 
    :isOpen="isOpen" 
    title="Оберіть КВЕД" 
    @close="$emit('close')"
  >
    <div class="flex flex-col h-[70vh] p-2">
      <div class="mb-6 relative group">
        <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" :size="20" />
        <input 
          type="text" 
          v-model="kvedSearch" 
          placeholder="Пошук за кодом або назвою..." 
          class="w-full pl-12 pr-12 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none font-bold placeholder:text-gray-300 transition-all shadow-sm"
        >
        <button 
          v-if="kvedSearch" 
          @click="kvedSearch = ''"
          class="absolute right-4 top-1/2 -translate-y-1/2 p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X :size="18" />
        </button>
      </div>
      
      <div class="flex-1 overflow-y-auto custom-scrollbar border-2 border-gray-100 rounded-3xl bg-gray-50/50">
        <div v-for="section in filteredKveds" :key="section.id" class="border-b border-gray-100 last:border-0 overflow-hidden bg-white">
          <button 
            type="button"
            @click="toggleSection(section.id)" 
            class="w-full flex items-center justify-between p-5 hover:bg-gray-50 text-left transition-colors sticky top-0 z-10 bg-white"
          >
            <span class="font-black text-sm text-gray-800 tracking-tight">{{ section.title }}</span>
            <div class="bg-gray-100 p-1 rounded-lg">
              <ChevronDown v-if="openSections[section.id]" :size="16" class="text-gray-500" />
              <ChevronRight v-else :size="16" class="text-gray-400" />
            </div>
          </button>
          
          <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
            <div v-if="openSections[section.id] || kvedSearch" class="bg-white border-t border-gray-50">
              <div v-for="group in section.groups" :key="group.id" class="border-b border-gray-50 last:border-0">
                <div class="px-6 py-2 bg-gray-50/50 text-[9px] font-black text-gray-400 uppercase tracking-widest">
                  {{ group.title }}
                </div>
                <div class="divide-y divide-gray-50">
                  <button 
                    v-for="item in group.items" 
                    :key="item.code" 
                    type="button"
                    @click="toggleKved(item)" 
                    class="w-full text-left px-6 py-4 flex items-center gap-5 hover:bg-blue-50 transition-all group"
                  >
                    <div 
                      class="w-6 h-6 rounded-lg border-2 flex items-center justify-center shrink-0 transition-all bg-white"
                      :class="isKvedSelected(item.code) ? 'bg-blue-600 border-blue-600 shadow-lg shadow-blue-100' : 'border-gray-200 group-hover:border-blue-300'"
                    >
                      <Check v-if="isKvedSelected(item.code)" :size="14" class="text-white" stroke-width="3" />
                    </div>
                    <div class="flex-grow">
                      <div class="flex items-center gap-3 mb-1">
                        <span class="font-black font-mono text-sm text-gray-900 group-hover:text-blue-600" v-html="highlightMatch(item.code, kvedSearch)"></span>
                        <div class="flex gap-1">
                          <span v-for="g in item.allowedGroups" :key="g" class="text-[9px] font-black bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded border border-gray-100">
                            {{ g }} ГР
                          </span>
                        </div>
                      </div>
                      <div class="text-sm text-gray-600 font-medium leading-relaxed" v-html="highlightMatch(item.name, kvedSearch)"></div>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </transition>
        </div>
        <div v-if="kvedSearch && filteredKveds.length === 0" class="p-12 text-center">
          <div class="text-4xl mb-4 text-gray-300">🔍</div>
          <p class="font-black text-gray-500 uppercase tracking-widest text-sm">Нічого не знайдено</p>
          <p class="text-xs text-gray-400 mt-2 italic font-medium">Спробуйте змінити запит або код</p>
        </div>
      </div>

      <div class="pt-6 mt-auto flex justify-end">
        <button 
          type="button" 
          @click="$emit('close')" 
          class="px-10 py-4 bg-gray-900 text-white rounded-2xl font-black hover:bg-black transition-all shadow-xl active:scale-95"
        >
          Готово
        </button>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e2e8f0; border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #cbd5e1; }
</style>
