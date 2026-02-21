<script setup>
import { computed } from 'vue';
import { RotateCcw } from 'lucide-vue-next';

const props = defineProps({
  filters: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:filters', 'reset']);

const localFilters = computed({
  get: () => props.filters,
  set: (val) => emit('update:filters', val)
});

const resetFilters = () => {
  emit('reset');
};
</script>

<template>
  <div class="bg-white p-4 sm:p-8 rounded-[1.5rem] sm:rounded-[2.5rem] border border-gray-100 mb-6 sm:mb-10 shadow-2xl shadow-gray-200/50 flex flex-wrap items-end gap-4 sm:gap-6">
    <div class="flex-1 min-w-[200px] space-y-2">
      <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Період</label>
      <div class="flex items-center gap-2 sm:gap-3">
        <input 
          type="date" 
          v-model="localFilters.startDate" 
          class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 text-sm"
        >
        <span class="text-gray-300">—</span>
        <input 
          type="date" 
          v-model="localFilters.endDate" 
          class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 text-sm"
        >
      </div>
    </div>
    
    <div class="w-full md:w-48 space-y-2">
      <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Тип</label>
      <select 
        v-model="localFilters.type" 
        class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 appearance-none text-sm"
      >
        <option value="">Всі операції</option>
        <option value="income">Тільки доходи</option>
        <option value="expense">Тільки витрати</option>
      </select>
    </div>

    <button 
      @click="resetFilters"
      class="h-[52px] px-6 text-gray-400 hover:text-red-500 font-bold flex items-center gap-2 transition-colors border-2 border-transparent hover:border-red-50 rounded-xl"
    >
      <RotateCcw :size="18" />
      Скинути
    </button>
  </div>
</template>
