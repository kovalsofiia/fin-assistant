<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { supabase } from '@/supabase';
import BaseModal from '@/components/common/BaseModal.vue';
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import { Plus, Pencil, Trash2, RotateCcw, Calendar, Tag, FileText, DollarSign, ArrowUpRight, ArrowDownLeft, Info } from 'lucide-vue-next';

const store = useTransactionStore();
const userId = ref(null);

// --- UI Прапорці ---
const isModalOpen = ref(false);
const isCategoryModalOpen = ref(false); 
const isSubmitting = ref(false);
const editingTxId = ref(null); 

// --- 1. Фільтри ---
watch(() => store.filters, () => {
  store.fetchTransactions();
}, { deep: true });

// --- 2. Форма Транзакції ---
const initialFormState = {
  type: 'expense',
  amount: '',
  date: new Date().toISOString().split('T')[0], 
  category_id: '',
  description: '',
  currency: 'UAH',
  manual_rate: '',
  isZed: false
};
const form = reactive({ ...initialFormState });

// --- 3. Форма Категорії ---
const newCategoryName = ref('');

// --- Завантаження даних ---
onMounted(async () => {
  const { data: { user } } = await supabase.auth.getUser();
  if (user) {
    userId.value = user.id;
    await store.fetchInitialData();
  }
});

const availableCategories = computed(() => {
  const type = form.type; 
  if (store.categories && store.categories[type]) {
     return store.categories[type];
  }
  return []; 
});

// --- Дії (Actions) ---
const openCreateModal = () => {
  editingTxId.value = null; 
  Object.assign(form, initialFormState); 
  setTimeout(() => autoSelectCategory(), 10);
  isModalOpen.value = true;
};

const submitTransaction = async () => {
  if (form.amount <= 0) return;
  isSubmitting.value = true;

  try {
    const payload = {
      user_id: userId.value,
      category_id: form.category_id,
      type: form.type,
      amount: parseFloat(form.amount),
      date: form.date,
      description: form.description,
      currency: form.isZed ? form.currency : 'UAH',
      manual_rate: (form.isZed && form.manual_rate) ? parseFloat(form.manual_rate) : null
    };

    if (editingTxId.value) {
      await store.editTransaction(editingTxId.value, userId.value, payload);
    } else {
      await store.addTransaction(payload);
    }
    isModalOpen.value = false;
  } catch (e) {
    console.error(e);
  } finally {
    isSubmitting.value = false;
  }
};

const deleteTx = async (id) => {
  if (confirm('Ви впевнені?')) {
    await store.deleteTransaction(id, userId.value);
  }
};

const submitNewCategory = async () => {
  if (!newCategoryName.value.trim()) return;
  try {
    await store.createNewCategory({
      name: newCategoryName.value,
      type: form.type,
      user_id: userId.value
    });
    newCategoryName.value = '';
    isCategoryModalOpen.value = false;
    const list = availableCategories.value;
    if (list.length > 0) {
       form.category_id = list[list.length - 1].id;
    }
  } catch (e) {
    console.error(e);
  }
};

const deleteCategory = async (catId) => {
  if (confirm('Видалити цю категорію?')) {
    try {
      await store.removeCategory(catId, userId.value);
      if (form.category_id === catId) {
        form.category_id = '';
      }
    } catch (e) {
      alert(e.response?.data?.detail || "Помилка видалення");
    }
  }
};

const getCategoryName = (id) => {
  if (!store.categories.all) return '...';
  const found = store.categories.all.find(c => c.id === id);
  return found ? found.name : '...';
};

const originalEditingType = ref(null);

const openEditModal = (tx) => {
  editingTxId.value = tx.transaction_id;
  originalEditingType.value = tx.transaction_type; 
  form.type = tx.transaction_type;
  form.amount = tx.amount_original || tx.transaction_amount; 
  form.date = tx.transaction_date.split('T')[0]; 
  form.category_id = tx.category_id;
  form.description = tx.notes;
  form.isZed = tx.is_foreign_currency;
  form.currency = tx.currency_code;
  form.manual_rate = tx.exchange_rate === 1.0 ? '' : tx.exchange_rate;
  isModalOpen.value = true;
};

const handleTypeChange = (newType) => {
  if (editingTxId.value && newType !== originalEditingType.value) {
    if (!confirm(`Змінити тип на ${newType === 'income' ? 'Дохід' : 'Витрата'}?`)) return;
  }
  form.type = newType;
  form.category_id = '';
  if (availableCategories.value.length > 0) {
    form.category_id = availableCategories.value[0].id;
  }
};

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

watch(() => form.isZed, () => autoSelectCategory());
watch(() => form.type, () => setTimeout(() => autoSelectCategory(), 10));
</script>

<template>
  <div class="max-w-6xl mx-auto p-8 animate-fade-in font-sans">
    <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
      <div>
        <h1 class="text-4xl font-black text-gray-900 tracking-tight">Транзакції</h1>
        <p class="text-gray-500 font-medium mt-1">Керуйте своїми доходами та витратами</p>
      </div>
      <button 
        @click="openCreateModal"
        class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-8 py-4 rounded-2xl font-black shadow-xl shadow-blue-200 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center gap-3"
      >
        <Plus :size="20" stroke-width="3" />
        Додати запис
      </button>
    </header>

    <!-- Filters Bar -->
    <div class="bg-white p-8 rounded-[2rem] border border-gray-100 mb-10 shadow-2xl shadow-gray-200/50 flex flex-wrap items-end gap-6">
      <div class="flex-1 min-w-[200px] space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Період</label>
        <div class="flex items-center gap-3">
          <input type="date" v-model="store.filters.startDate" class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700">
          <span class="text-gray-300">—</span>
          <input type="date" v-model="store.filters.endDate" class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700">
        </div>
      </div>
      
      <div class="w-full md:w-48 space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Тип</label>
        <select v-model="store.filters.type" class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 appearance-none">
          <option value="">Всі операції</option>
          <option value="income">Тільки доходи</option>
          <option value="expense">Тільки витрати</option>
        </select>
      </div>

      <button 
        @click="store.filters = { startDate:'', endDate:'', type:'' }"
        class="h-[52px] px-6 text-gray-400 hover:text-red-500 font-bold flex items-center gap-2 transition-colors border-2 border-transparent hover:border-red-50 rounded-xl"
      >
        <RotateCcw :size="18" />
        Скинути
      </button>
    </div>

    <!-- Table Section -->
    <div class="bg-white rounded-[2.5rem] shadow-2xl shadow-gray-200/50 border border-gray-50 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left">
          <thead>
            <tr class="bg-gray-50/50 border-b border-gray-50">
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Дата</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Категорія</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Коментар</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest text-right">Сума</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest text-right">Дії</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <!-- Skeleton Loading State -->
            <template v-if="store.isLoading">
              <tr v-for="i in 8" :key="i" class="animate-pulse">
                <td class="px-8 py-6">
                  <div class="flex items-center gap-3">
                    <SkeletonLoader width="40px" height="40px" borderRadius="12px" />
                    <SkeletonLoader width="100px" height="20px" />
                  </div>
                </td>
                <td class="px-8 py-6"><SkeletonLoader width="120px" height="24px" borderRadius="12px" /></td>
                <td class="px-8 py-6"><SkeletonLoader width="150px" height="20px" /></td>
                <td class="px-8 py-6">
                  <div class="flex flex-col items-end gap-1">
                    <SkeletonLoader width="100px" height="24px" />
                    <SkeletonLoader width="60px" height="12px" />
                  </div>
                </td>
                <td class="px-8 py-6 flex justify-end gap-2">
                  <SkeletonLoader width="44px" height="44px" borderRadius="12px" />
                  <SkeletonLoader width="44px" height="44px" borderRadius="12px" />
                </td>
              </tr>
            </template>

            <!-- Actual Data -->
            <template v-else>
              <tr v-for="tx in store.transactions" :key="tx.transaction_id" class="group hover:bg-gray-50/50 transition-all">
                <td class="px-8 py-6">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 group-hover:bg-white group-hover:shadow-sm transition-all">
                      <Calendar :size="18" />
                    </div>
                    <span class="font-bold text-gray-700">{{ new Date(tx.transaction_date).toLocaleDateString('uk-UA') }}</span>
                  </div>
                </td>
                <td class="px-8 py-6">
                  <div 
                    class="inline-flex items-center px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-wider"
                    :class="tx.transaction_type === 'income' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                  >
                    {{ getCategoryName(tx.category_id) }}
                  </div>
                </td>
                <td class="px-8 py-6">
                  <span class="text-gray-500 font-medium italic">{{ tx.notes || '—' }}</span>
                </td>
                <td class="px-8 py-6 text-right">
                  <div class="flex flex-col items-end">
                    <div class="text-lg font-black tracking-tight" :class="tx.transaction_type === 'income' ? 'text-green-600' : 'text-red-600'">
                      {{ tx.transaction_type === 'income' ? '+' : '-' }}
                      {{ tx.transaction_amount.toLocaleString() }} ₴
                    </div>
                    <div v-if="tx.is_foreign_currency" class="text-[10px] font-black uppercase text-gray-400 mt-0.5 flex items-center gap-1">
                      {{ tx.amount_original }} {{ tx.currency_code }} <span class="text-gray-200">•</span> {{ tx.exchange_rate }}
                    </div>
                  </div>
                </td>
                <td class="px-8 py-6 text-right">
                  <div class="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-all translate-x-4 group-hover:translate-x-0">
                    <button @click="openEditModal(tx)" class="p-3 bg-white shadow-sm border border-gray-100 rounded-xl text-blue-600 hover:bg-blue-600 hover:text-white transition-all">
                      <Pencil :size="18" />
                    </button>
                    <button @click="deleteTx(tx.transaction_id)" class="p-3 bg-white shadow-sm border border-gray-100 rounded-xl text-red-500 hover:bg-red-500 hover:text-white transition-all">
                      <Trash2 :size="18" />
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="store.transactions.length === 0">
                <td colspan="5" class="px-8 py-20 text-center">
                  <div class="flex flex-col items-center gap-4">
                    <div class="w-20 h-20 bg-gray-50 rounded-3xl flex items-center justify-center text-gray-200 mb-2">
                      <FileText :size="40" />
                    </div>
                    <p class="font-black text-gray-300 uppercase tracking-widest text-sm">
                      Записів не знайдено
                    </p>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Transaction Modal Content -->
    <BaseModal 
      :isOpen="isModalOpen" 
      :title="editingTxId ? 'Редагувати запис' : 'Створити запис'" 
      @close="isModalOpen = false"
    >
      <form @submit.prevent="submitTransaction" class="space-y-8">
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

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="space-y-2">
            <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1 flex items-center gap-2">
              <DollarSign :size="14" /> Сума
            </label>
            <input type="number" step="0.01" v-model="form.amount" required class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-black text-gray-800 text-xl">
          </div>
          <div class="space-y-2">
            <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1 flex items-center gap-2">
              <Calendar :size="14" /> Дата
            </label>
            <input type="date" v-model="form.date" required class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800">
          </div>
        </div>

        <!-- ZED/FX Row (Multi-currency) -->
        <div class="group">
          <label class="flex items-center gap-4 bg-blue-50/50 p-5 rounded-3xl border-2 border-dashed border-blue-100 cursor-pointer hover:bg-blue-50 transition-all">
            <div class="relative w-6 h-6">
              <input type="checkbox" v-model="form.isZed" class="peer appearance-none w-6 h-6 border-2 border-blue-200 checked:bg-blue-600 checked:border-blue-600 rounded-lg transition-all">
              <div class="absolute inset-0 flex items-center justify-center text-white opacity-0 peer-checked:opacity-100 pointer-events-none">
                <Check :size="14" stroke-width="4" />
              </div>
            </div>
            <span class="font-black text-blue-900 uppercase tracking-widest text-xs">Операція в іноземній валюті</span>
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
            <button @click="isCategoryModalOpen = true" type="button" class="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:underline underline-offset-4">
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
      </form>
    </BaseModal>

    <!-- Create Category Modal -->
    <BaseModal 
      :isOpen="isCategoryModalOpen" 
      title="Нова категорія" 
      @close="isCategoryModalOpen = false"
    >
      <div class="space-y-8">
        <div class="p-6 bg-gray-50 rounded-3xl border border-gray-100">
           <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Тип операції</p>
           <p class="font-black text-xl" :class="form.type === 'income' ? 'text-green-600' : 'text-red-600'">
             {{ form.type === 'income' ? 'Дохід' : 'Витрата' }}
           </p>
        </div>
        
        <div class="space-y-2">
          <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Назва категорії</label>
          <input type="text" v-model="newCategoryName" placeholder="Напр. Фріланс" autofocus class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-black text-gray-800">
        </div>

        <button 
          @click="submitNewCategory"
          class="w-full py-5 rounded-3xl font-black bg-gray-900 text-white hover:bg-black transition-all shadow-xl shadow-gray-200 active:scale-[0.98]"
        >
          Створити категорію
        </button>

        <div v-if="availableCategories.filter(c => c.user_id).length > 0" class="pt-8 border-t border-gray-100">
          <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-4 px-1">Ваші власні категорії</p>
          <div class="space-y-3">
            <div 
              v-for="cat in availableCategories.filter(c => c.user_id)" 
              :key="cat.id"
              class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-50 group transition-all hover:bg-white hover:border-blue-100 hover:shadow-sm"
            >
              <span class="font-bold text-gray-700">{{ cat.name }}</span>
              <button 
                @click="deleteCategory(cat.id)"
                class="p-2 text-gray-300 hover:text-red-500 transition-colors"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>