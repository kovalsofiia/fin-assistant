<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { supabase } from '@/services/supabase';
import BaseModal from '@/components/common/BaseModal.vue';
import TransactionModal from '@/components/dashboard/TransactionModal.vue';
import TransactionForm from '@/components/common/TransactionForm.vue';
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import { Check, Plus, Pencil, Trash2, RotateCcw, Calendar, Tag, FileText, DollarSign, ArrowUpRight, ArrowDownLeft, Info, X } from 'lucide-vue-next';
import api from '@/services/api';

const store = useTransactionStore();
const userId = ref(null);

// --- UI Прапорці ---
const isModalOpen = ref(false);
const isCategoryModalOpen = ref(false); 
const isSubmitting = ref(false);
const editingTxId = ref(null);
const fopSettings = ref(null);
const userProfile = ref(null);

// --- New Detail Modal & Selection ---
const isDetailModalOpen = ref(false);
const selectedTransaction = ref(null);
const selectedTxIds = ref([]);

const openTransactionDetails = (tx) => {
  selectedTransaction.value = tx;
  isDetailModalOpen.value = true;
};

const toggleSelection = (txId) => {
  const index = selectedTxIds.value.indexOf(txId);
  if (index > -1) {
    selectedTxIds.value.splice(index, 1);
  } else {
    selectedTxIds.value.push(txId);
  }
};

const toggleSelectAll = () => {
  if (selectedTxIds.value.length === store.transactions.length) {
    selectedTxIds.value = [];
  } else {
    selectedTxIds.value = store.transactions.map(t => t.transaction_id);
  }
};

const deleteBatch = async () => {
  if (selectedTxIds.value.length === 0) return;
  if (confirm(`Видалити вибрані транзакції (${selectedTxIds.value.length})?`)) {
    try {
      await store.deleteTransactionsBatch(userId.value, selectedTxIds.value);
      selectedTxIds.value = [];
    } catch (e) {
      alert("Помилка при видаленні");
    }
  }
};



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
const editingCategoryId = ref(null); // Додано для редагування категорій

// --- Завантаження даних ---
onMounted(async () => {
  const { data: { user } } = await supabase.auth.getUser();
  if (user) {
    userId.value = user.id;
    await store.fetchInitialData();
    
    // Отримуємо налаштування ФОП для валідації ЗЕД
    try {
      const [profileRes, settingsRes] = await Promise.all([
        api.getProfile(user.id),
        api.getFopSettings(user.id)
      ]);
      userProfile.value = profileRes.data;
      fopSettings.value = settingsRes.data;
    } catch (e) {
      console.error("Error loading user context:", e);
    }
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
    if (editingCategoryId.value) {
      // Режим редагування
      await store.modifyCategory(editingCategoryId.value, userId.value, {
        name: newCategoryName.value
      });
    } else {
      // Режим створення
      await store.createNewCategory({
        name: newCategoryName.value,
        type: form.type,
        user_id: userId.value
      });
    }
    
    newCategoryName.value = '';
    editingCategoryId.value = null;
    isCategoryModalOpen.value = false;
    
    const list = availableCategories.value;
    if (list.length > 0 && !editingCategoryId.value) {
       form.category_id = list[list.length - 1].id;
    }
  } catch (e) {
    console.error(e);
    alert(e.response?.data?.detail || "Помилка при збереженні категорії");
  }
};

const openEditCategory = (cat) => {
  editingCategoryId.value = cat.id;
  newCategoryName.value = cat.name;
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

const handleUpdate = async () => {
  await store.fetchTransactions();
  isDetailModalOpen.value = false;
};
</script>

<template>
  <div class="max-w-6xl mx-auto p-4 sm:p-8 animate-fade-in font-sans">
    <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8 sm:mb-12">
      <div>
        <h1 class="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight">Транзакції</h1>
        <p class="text-gray-500 font-medium mt-1">Керуйте своїми доходами та витратами</p>
      </div>
      <div class="flex flex-col md:flex-row items-center gap-4 w-full md:w-auto">
        <button 
          v-if="selectedTxIds.length > 0"
          @click="deleteBatch"
          class="w-full md:w-auto bg-red-50 text-red-600 px-6 py-4 rounded-2xl font-black border-2 border-red-100 hover:bg-red-100 transition-all flex items-center justify-center gap-2"
        >
          <Trash2 :size="18" />
          Видалити ({{ selectedTxIds.length }})
        </button>
        <button 
          v-if="selectedTxIds.length > 0"
          @click="selectedTxIds = []"
          class="w-full md:w-auto bg-gray-50 text-gray-500 px-6 py-4 rounded-2xl font-black hover:bg-gray-100 transition-all"
        >
          Скасувати
        </button>
        <button 
          @click="openCreateModal"
          class="w-full md:w-auto bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-8 py-4 rounded-2xl font-black shadow-xl shadow-blue-200 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-3"
        >
          <Plus :size="20" stroke-width="3" />
          Додати запис
        </button>
      </div>
    </header>

    <!-- Filters Bar -->
    <div class="bg-white p-4 sm:p-8 rounded-[1.5rem] sm:rounded-[2.5rem] border border-gray-100 mb-6 sm:mb-10 shadow-2xl shadow-gray-200/50 flex flex-wrap items-end gap-4 sm:gap-6">
      <div class="flex-1 min-w-[200px] space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Період</label>
        <div class="flex items-center gap-2 sm:gap-3">
          <input type="date" v-model="store.filters.startDate" class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 text-sm">
          <span class="text-gray-300">—</span>
          <input type="date" v-model="store.filters.endDate" class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 text-sm">
        </div>
      </div>
      
      <div class="w-full md:w-48 space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Тип</label>
        <select v-model="store.filters.type" class="w-full px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-xl outline-none transition-all font-bold text-gray-700 appearance-none text-sm">
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

    <!-- Mobile Transactions List (sm hidden) -->
    <div class="block sm:hidden space-y-4">
      <div v-if="store.isLoading" class="space-y-4">
        <div v-for="i in 5" :key="i" class="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm animate-pulse space-y-3">
          <div class="flex justify-between items-center">
            <SkeletonLoader width="100px" height="20px" />
            <SkeletonLoader width="80px" height="24px" borderRadius="10px" />
          </div>
          <div class="flex justify-between items-end">
            <div class="space-y-2">
              <SkeletonLoader width="120px" height="16px" />
              <SkeletonLoader width="60px" height="12px" />
            </div>
            <div class="flex gap-2">
              <SkeletonLoader width="36px" height="36px" borderRadius="10px" />
              <SkeletonLoader width="36px" height="36px" borderRadius="10px" />
            </div>
          </div>
        </div>
      </div>

      <template v-else>
        <div 
          v-for="tx in store.transactions" 
          :key="tx.transaction_id" 
          class="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm active:scale-[0.98] transition-all space-y-4 relative"
          :class="{ 'border-blue-500 bg-blue-50/30': selectedTxIds.includes(tx.transaction_id) }"
        >
          <!-- Selection Checkbox (Mobile) -->
          <div class="absolute top-4 right-4 z-10">
            <input 
              type="checkbox" 
              :checked="selectedTxIds.includes(tx.transaction_id)" 
              @click.stop="toggleSelection(tx.transaction_id)"
              class="w-5 h-5 rounded-lg border-2 border-gray-200 checked:bg-blue-600 checked:border-blue-600 transition-all"
            >
          </div>

          <div class="flex justify-between items-start" @click="openTransactionDetails(tx)">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400">
                <Calendar :size="18" />
              </div>
              <div class="flex flex-col">
                <span class="text-xs font-black text-gray-400 uppercase tracking-widest">{{ new Date(tx.transaction_date).toLocaleDateString('uk-UA') }}</span>
                <span class="font-bold text-gray-800">{{ getCategoryName(tx.category_id) }}</span>
              </div>
            </div>
            <div 
              class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider"
              :class="tx.transaction_type === 'income' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
            >
              {{ tx.transaction_type === 'income' ? 'Дохід' : 'Витрата' }}
            </div>
          </div>

          <div v-if="tx.notes" class="text-sm text-gray-500 font-medium italic bg-gray-50 p-3 rounded-xl">
            "{{ tx.notes }}"
          </div>

          <div class="flex justify-between items-end pt-2 border-t border-gray-50">
            <div class="flex flex-col">
              <div class="text-xl font-black tracking-tight" :class="tx.transaction_type === 'income' ? 'text-green-600' : 'text-red-600'">
                {{ tx.transaction_type === 'income' ? '+' : '-' }}
                {{ tx.transaction_amount.toLocaleString() }} ₴
              </div>
              <div v-if="tx.is_foreign_currency" class="text-[10px] font-black uppercase text-gray-400 mt-1 flex items-center gap-1">
                {{ tx.amount_original }} {{ tx.currency_code }} <span class="text-gray-200">•</span> {{ tx.exchange_rate }}
              </div>
            </div>
            
            <div class="flex gap-2">
              <button @click.stop="openTransactionDetails(tx)" class="p-2.5 bg-gray-50 text-blue-600 rounded-xl hover:bg-blue-600 hover:text-white transition-all">
                <Info :size="18" />
              </button>
              <button @click.stop="deleteTx(tx.transaction_id)" class="p-2.5 bg-gray-50 text-red-500 rounded-xl hover:bg-red-500 hover:text-white transition-all">
                <Trash2 :size="18" />
              </button>
            </div>
          </div>
        </div>

        <div v-if="store.transactions.length === 0" class="py-12 text-center bg-white rounded-3xl border-2 border-dashed border-gray-100">
           <FileText :size="40" class="mx-auto text-gray-200 mb-2" />
           <p class="font-black text-gray-300 uppercase tracking-widest text-xs">Записів не знайдено</p>
        </div>
      </template>
    </div>

    <!-- Table Section (Desktop only) -->
    <div class="hidden sm:block bg-white rounded-[2.5rem] shadow-2xl shadow-gray-200/50 border border-gray-50 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left">
          <thead>
            <tr class="bg-gray-50/50 border-b border-gray-50">
              <th class="px-8 py-6 w-10">
                <input 
                  type="checkbox" 
                  :checked="selectedTxIds.length === store.transactions.length && store.transactions.length > 0" 
                  @change="toggleSelectAll"
                  class="w-5 h-5 rounded-lg border-2 border-gray-200 checked:bg-blue-600 checked:border-blue-600 transition-all cursor-pointer"
                >
              </th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Дата</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Категорія</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Коментар</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest text-right">Сума</th>
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
              <tr 
                v-for="tx in store.transactions" 
                :key="tx.transaction_id" 
                class="group hover:bg-gray-50/50 transition-all cursor-pointer"
                :class="{ 'bg-blue-50/30': selectedTxIds.includes(tx.transaction_id) }"
                @click="openTransactionDetails(tx)"
              >
                <td class="px-8 py-6" @click.stop>
                  <input 
                    type="checkbox" 
                    :checked="selectedTxIds.includes(tx.transaction_id)" 
                    @change="toggleSelection(tx.transaction_id)"
                    class="w-5 h-5 rounded-lg border-2 border-gray-200 checked:bg-blue-600 checked:border-blue-600 transition-all cursor-pointer"
                  >
                </td>
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
      <form @submit.prevent="submitTransaction">
        <TransactionForm 
          v-model="form"
          :fopSettings="fopSettings"
          :isSubmitting="isSubmitting"
          @add-category="isCategoryModalOpen = true"
        />
      </form>
    </BaseModal>

    <BaseModal 
      :isOpen="isCategoryModalOpen" 
      :title="editingCategoryId ? 'Редагувати категорію' : 'Нова категорія'" 
      @close="isCategoryModalOpen = false; editingCategoryId = null; newCategoryName = '';"
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
          {{ editingCategoryId ? 'Зберегти назву' : 'Створити категорію' }}
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
              <div class="flex items-center gap-1">
                <button 
                  @click="openEditCategory(cat)"
                  class="p-2 text-gray-300 hover:text-blue-500 transition-colors"
                >
                  <Pencil :size="16" />
                </button>
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
      </div>
    </BaseModal>

    <!-- Transaction Detail Modal -->
    <TransactionModal 
      :isOpen="isDetailModalOpen"
      :transaction="selectedTransaction"
      :userId="userId"
      :fopSettings="fopSettings"
      @close="isDetailModalOpen = false; selectedTransaction = null"
      @updated="handleUpdate"
      @deleted="handleUpdate"
    />
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>