<script setup>
import { computed, watch } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { 
  Calendar, Tag, FileText, DollarSign, ArrowUpRight, ArrowDownLeft, Check, Info 
} from 'lucide-vue-next';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  },
  fopSettings: {
    type: Object,
    default: null
  },
  isSubmitting: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue', 'add-category']);

const txStore = useTransactionStore();

const form = props.modelValue;

const availableCategories = computed(() => {
  const type = form.type;
  if (txStore.categories && txStore.categories[type]) {
    return txStore.categories[type];
  }
  return [];
});

const autoSelectCategory = () => {
  const list = availableCategories.value;
  if (!list || list.length === 0) return;
  
  if (form.type === 'income') {
    const searchKey = form.isZed ? 'ЗЕД' : 'Гривня'; 
    const found = list.find(c => c.name.toLowerCase().includes(searchKey.toLowerCase()));
    if (found) form.category_id = found.id;
    else if (!form.category_id) form.category_id = list[0].id;
  } else {
    if (!form.category_id && list.length > 0) form.category_id = list[0].id;
  }
};

const handleTypeChange = (newType) => {
  form.type = newType;
  form.category_id = '';
  autoSelectCategory();
};

// Listen for changes in isZed to trigger auto-selection
watch(() => form.isZed, () => {
  autoSelectCategory();
});

// Sync type changes with categories
watch(() => form.type, () => {
  setTimeout(() => autoSelectCategory(), 10);
});

const isZedRestricted = computed(() => {
  return props.fopSettings?.fop_group === 1 || props.fopSettings?.fop_group === 4;
});

</script>

<template>
  <div class="space-y-6 sm:space-y-8">
    <!-- Type Selector -->
    <div class="flex p-2 bg-gray-100 rounded-[2rem] gap-2">
      <button 
        type="button"
        class="flex-1 py-4 px-6 rounded-[1.5rem] font-black text-sm uppercase tracking-widest flex items-center justify-center gap-3 transition-all"
        :class="form.type === 'expense' ? 'bg-white shadow-xl text-red-600' : 'text-gray-400 hover:text-gray-600'"
        @click.prevent="handleTypeChange('expense')"
      >
        <ArrowDownLeft :size="18" stroke-width="3" />
        Витрата
      </button>
      <button 
        type="button"
        class="flex-1 py-4 px-6 rounded-[1.5rem] font-black text-sm uppercase tracking-widest flex items-center justify-center gap-3 transition-all"
        :class="form.type === 'income' ? 'bg-white shadow-xl text-green-600' : 'text-gray-400 hover:text-gray-600'"
        @click.prevent="handleTypeChange('income')"
      >
        <ArrowUpRight :size="18" stroke-width="3" />
        Дохід
      </button>
    </div>

    <!-- Amount & Date -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1 flex items-center gap-2">
          <DollarSign :size="14" /> Сума
        </label>
        <input 
          type="number" 
          step="0.01" 
          v-model="form.amount" 
          required 
          class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-black text-gray-800 text-xl"
        >
      </div>
      <div class="space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1 flex items-center gap-2">
          <Calendar :size="14" /> Дата
        </label>
        <input 
          type="date" 
          v-model="form.date" 
          required 
          class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800"
        >
      </div>
    </div>

    <!-- ZED/FX Row -->
    <div class="group">
      <label 
        class="flex items-center gap-4 bg-blue-50/50 p-5 rounded-3xl border-2 border-dashed border-blue-100 transition-all shadow-sm"
        :class="[isZedRestricted ? 'opacity-50 cursor-not-allowed grayscale' : 'cursor-pointer hover:bg-white hover:border-blue-200 hover:shadow-md']"
      >
        <div class="relative w-7 h-7 shrink-0">
          <input 
            type="checkbox" 
            v-model="form.isZed" 
            :disabled="isZedRestricted"
            class="peer appearance-none w-7 h-7 border-2 border-blue-200 checked:bg-blue-600 checked:border-blue-600 rounded-xl transition-all shadow-inner disabled:bg-gray-200 disabled:border-gray-300"
          >
          <div class="absolute inset-0 flex items-center justify-center text-white opacity-0 peer-checked:opacity-100 pointer-events-none transition-all scale-50 peer-checked:scale-100">
            <Check :size="16" stroke-width="4" />
          </div>
        </div>
        <div class="flex flex-col">
          <span class="font-black text-blue-900 uppercase tracking-widest text-[10px] group-hover:text-blue-600 transition-colors flex items-center gap-2">
            Операція в іноземній валюті
            <span v-if="isZedRestricted" class="bg-red-100 text-red-600 px-1.5 py-0.5 rounded text-[8px]">Заборонено для {{ fopSettings?.fop_group }} групи</span>
          </span>
          <span v-if="isZedRestricted" class="text-[9px] text-gray-500 font-medium mt-0.5">ФОП 1 та 4 груп не можуть здійснювати зовнішньоекономічну діяльність</span>
        </div>
      </label>
      
      <div v-if="form.isZed" class="mt-6 grid grid-cols-2 gap-4 animate-fade-in">
        <select v-model="form.currency" class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-700">
          <option value="USD">USD ($)</option>
          <option value="EUR">EUR (€)</option>
        </select>
        <input type="number" step="0.0001" v-model="form.manual_rate" placeholder="Курс (пусто = НБУ)" class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-700">
      </div>
    </div>

    <!-- Category Select -->
    <div class="space-y-2">
      <div class="flex justify-between items-center px-1">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
          <Tag :size="14" /> Категорія
        </label>
        <button @click="$emit('add-category')" type="button" class="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:underline underline-offset-4">
          + Створити
        </button>
      </div>
      <select v-model="form.category_id" required class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800">
         <option value="" disabled>Оберіть категорію</option>
         <option v-for="cat in availableCategories" :key="cat.id" :value="cat.id">
           {{ cat.name }} {{ cat.user_id ? '(своя)' : '' }}
         </option>
      </select>
    </div>

    <!-- Description -->
    <div class="space-y-2">
      <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1 flex items-center gap-2">
        <FileText :size="14" /> Опис
      </label>
      <textarea v-model="form.description" rows="2" class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800 resize-none"></textarea>
    </div>

    <button 
      type="submit" 
      :disabled="isSubmitting"
      class="w-full py-5 rounded-3xl font-black bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 transition-all shadow-xl shadow-blue-100 disabled:opacity-50 flex justify-center items-center gap-3 active:scale-[0.98]"
    >
      {{ isSubmitting ? 'Завантаження...' : 'Зберегти зміни' }}
    </button>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
