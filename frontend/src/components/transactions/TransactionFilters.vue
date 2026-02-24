<script setup>
import { computed, ref, watch, onMounted } from 'vue';
import { RotateCcw } from 'lucide-vue-next';
import { useTransactionStore } from '@/stores/transactionStore';

const props = defineProps({
  filters: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:filters', 'reset']);

const store = useTransactionStore();

const localFilters = computed({
  get: () => props.filters,
  set: (val) => emit('update:filters', val)
});

const quickDateFilter = ref('');

const applyDateFilter = (range) => {
  const today = new Date();
  let start = new Date();
  let end = new Date();
  
  if (range === 'today') {
    start = today;
    end = today;
  } else if (range === 'yesterday') {
    start.setDate(today.getDate() - 1);
    end.setDate(today.getDate() - 1);
  } else if (range === 'last_week') {
    start.setDate(today.getDate() - 7);
    end = today;
  } else if (range === 'last_two_weeks') {
    start.setDate(today.getDate() - 14);
    end = today;
  } else if (range === 'this_month') {
    start = new Date(today.getFullYear(), today.getMonth(), 1);
    end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  } else if (range === 'last_month') {
    start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    end = new Date(today.getFullYear(), today.getMonth(), 0);
  } else if (range === 'last_3_months') {
    start = new Date(today.getFullYear(), today.getMonth() - 3, 1);
    end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  }

  if (range && range !== 'custom') {
    // Timezone adjustment for local date string properly formatted (YYYY-MM-DD)
    const toIsoDate = (d) => {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };
    localFilters.value.startDate = toIsoDate(start);
    localFilters.value.endDate = toIsoDate(end);
  }
};

watch(quickDateFilter, (newVal) => {
  if (newVal === 'custom') {
    // Keep whatever is in the inputs
  } else if (newVal) {
    applyDateFilter(newVal);
  } else {
    localFilters.value.startDate = '';
    localFilters.value.endDate = '';
  }
});

const resetFilters = () => {
  quickDateFilter.value = '';
  emit('reset');
};

onMounted(() => {
  if (localFilters.value.startDate || localFilters.value.endDate) {
    quickDateFilter.value = 'custom';
  }
});
</script>

<template>
  <div class="bg-white p-4 sm:p-8 rounded-[1.5rem] sm:rounded-[2.5rem] border border-gray-100 mb-6 sm:mb-10 shadow-2xl shadow-gray-200/50 flex flex-col lg:flex-row lg:items-end gap-6">
    <!-- Period Section -->
    <div class="flex-grow space-y-2">
      <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Період</label>
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <select 
          v-model="quickDateFilter" 
          class="w-full sm:w-48 px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 appearance-none text-sm cursor-pointer"
        >
          <option value="">Весь час</option>
          <option value="today">Сьогодні</option>
          <option value="yesterday">Вчора</option>
          <option value="last_week">Останній тиждень</option>
          <option value="last_two_weeks">Останні два тижні</option>
          <option value="this_month">Цей місяць</option>
          <option value="last_month">Минулий місяць</option>
          <option value="last_3_months">Останні 3 місяці</option>
          <option value="custom">Інший період...</option>
        </select>
        
        <div class="flex flex-col sm:flex-row items-center gap-2 animate-fade-in flex-grow max-w-none sm:max-w-sm">
          <input 
            type="date" 
            v-model="localFilters.startDate" 
            @change="quickDateFilter = 'custom'"
            class="w-full px-3 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 text-sm"
          >
          <span class="text-gray-300 font-bold px-1 hidden sm:block">—</span>
          <input 
            type="date" 
            v-model="localFilters.endDate" 
            @change="quickDateFilter = 'custom'"
            class="w-full px-3 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 text-sm"
          >
        </div>
    </div>
  </div>
    
    <!-- Type & Category Filters -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 lg:flex lg:gap-6">
      <div class="sm:w-44 space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Тип</label>
        <select 
          v-model="localFilters.type" 
          class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 appearance-none text-sm cursor-pointer"
        >
          <option value="">Всі операції</option>
          <option value="income">Тільки доходи</option>
          <option value="expense">Тільки витрати</option>
        </select>
      </div>

      <div class="sm:w-44 space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Категорія</label>
        <select 
          v-model="localFilters.categoryId" 
          class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 appearance-none text-sm cursor-pointer"
        >
          <option value="">Всі категорії</option>
          <option v-for="cat in store.categories?.all || []" :key="cat.id" :value="cat.id">
            {{ cat.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center">
      <button 
        @click="resetFilters"
        title="Скинути фільтри"
        class="w-12 h-12 flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all border-2 border-transparent active:scale-95"
      >
        <RotateCcw :size="20" />
      </button>
    </div>
  </div>
</template>
