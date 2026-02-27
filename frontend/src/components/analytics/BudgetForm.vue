<script setup>
import { ref, onMounted } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { useBudgetStore } from '@/stores/budgetStore';
import { supabase } from '@/services/supabase';

const props = defineProps({
  budgetToEdit: { type: Object, default: null }
});

const emit = defineEmits(['close']);

const txStore = useTransactionStore();
const budgetStore = useBudgetStore();

const form = ref({
  category_id: '',
  amount: '',
  period: 'monthly'
});

const isSubmitting = ref(false);

onMounted(async () => {
  if (props.budgetToEdit) {
    form.value = {
      category_id: props.budgetToEdit.category_id || '',
      amount: props.budgetToEdit.amount,
      period: props.budgetToEdit.period
    };
  }
  if (!txStore.categories.expense.length) {
    await txStore.fetchCategories();
  }
});

const submitHandler = async () => {
  isSubmitting.value = true;
  try {
    const { data: { user } } = await supabase.auth.getUser();
    const payload = {
      user_id: user.id,
      category_id: form.value.category_id || null,
      amount: Number(form.value.amount),
      period: form.value.period
    };
    
    if (props.budgetToEdit) {
      await budgetStore.updateBudget(props.budgetToEdit.id, user.id, payload);
    } else {
      await budgetStore.createBudget(payload);
    }
    emit('close');
  } catch (e) {
    console.error(e);
    alert('Помилка збереження бюджету');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-fade-in">
    <div class="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <h2 class="text-2xl font-black text-gray-800 tracking-tight">
          {{ budgetToEdit ? 'Редагувати Бюджет' : 'Новий Бюджет' }}
        </h2>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 font-bold p-2 text-2xl transition-colors">&times;</button>
      </div>
      
      <form @submit.prevent="submitHandler" class="p-6 flex flex-col gap-6 overflow-y-auto">
        <div>
          <label class="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-wide">Категорія</label>
          <select 
            v-model="form.category_id" 
            class="w-full px-4 py-3 bg-gray-50 border-2 border-gray-100 rounded-2xl font-bold text-gray-800 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all outline-none appearance-none"
          >
            <option value="">Загальний бюджет (всі витрати)</option>
            <option v-for="cat in txStore.categories.expense" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </option>
          </select>
        </div>

        <div>
           <label class="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-wide">Сума (Ліміт)</label>
          <div class="relative">
            <input 
              v-model="form.amount" 
              type="number" 
              min="1" 
              step="0.01" 
              required
              class="w-full px-4 py-3 bg-gray-50 border-2 border-gray-100 rounded-2xl font-black text-gray-900 text-xl focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all outline-none"
              placeholder="0.00"
            />
            <span class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold">UAH</span>
          </div>
        </div>

        <div>
           <label class="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-wide">Період</label>
          <select 
            v-model="form.period" 
            class="w-full px-4 py-3 bg-gray-50 border-2 border-gray-100 rounded-2xl font-bold text-gray-800 focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all outline-none appearance-none"
          >
            <option value="weekly">Тижневий</option>
            <option value="monthly">Місячний</option>
            <option value="yearly">Річний</option>
          </select>
        </div>

        <div class="flex gap-4 pt-4 mt-2 border-t border-gray-100">
          <button 
            type="button" 
            @click="emit('close')" 
            class="flex-1 py-4 bg-gray-100 hover:bg-gray-200 text-gray-700 font-black rounded-2xl transition-colors"
          >
            Скасувати
          </button>
          <button 
            type="submit" 
            :disabled="isSubmitting"
            class="flex-1 py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-black rounded-2xl transition-colors shadow-lg shadow-indigo-200 disabled:opacity-50"
          >
            {{ isSubmitting ? 'Збереження...' : 'Зберегти' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
