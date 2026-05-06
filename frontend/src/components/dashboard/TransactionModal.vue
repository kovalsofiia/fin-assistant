<script setup>
import { ref, reactive, computed, watch } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import BaseModal from '@/components/common/BaseModal.vue';
import CategoryModal from '@/components/common/CategoryModal.vue';
import TransactionForm from '@/components/common/TransactionForm.vue';
import { 
  Pencil, Trash2, Calendar, Tag, FileText, 
  ArrowUpRight, ArrowDownLeft, CreditCard, User
} from 'lucide-vue-next';
import api from '@/services/api';
import { useNotificationStore } from '@/stores/notificationStore';

const notificationStore = useNotificationStore();

const props = defineProps({
  isOpen: Boolean,
  transaction: Object,
  fopSettings: Object,
  userId: String
});

const emit = defineEmits(['close', 'updated', 'deleted']);

const txStore = useTransactionStore();
const isEditing = ref(false);
const isSubmitting = ref(false);

// Category creation state
const isCategoryModalOpen = ref(false);

const initialFormState = {
  type: 'expense',
  amount: '',
  date: new Date().toISOString().split('T')[0],
  category_id: '',
  description: '',
  currency: 'UAH',
  manual_rate: '',
  isZed: false,
  is_fop: true
};

const form = reactive({ ...initialFormState });

const resetForm = () => {
  Object.assign(form, initialFormState);
};

// Initialize form when transaction changes or editing starts
watch(() => props.transaction, (newTx) => {
  if (newTx) {
    Object.assign(form, {
      type: newTx.transaction_type,
      amount: newTx.amount_original || newTx.transaction_amount,
      date: newTx.transaction_date.split('T')[0],
      category_id: newTx.category_id,
      description: newTx.notes || '',
      currency: newTx.currency_code || 'UAH',
      manual_rate: newTx.exchange_rate === 1.0 ? '' : newTx.exchange_rate,
      isZed: newTx.is_foreign_currency,
      is_fop: newTx.is_fop !== false
    });
  } else {
    resetForm();
  }
}, { immediate: true });

// Reset editing state when modal opens/closes
watch(() => props.isOpen, (newVal) => {
  if (!newVal) {
    setTimeout(() => {
      isEditing.value = false;
      resetForm();
    }, 300); // Wait for transition
  }
});

const availableCategories = computed(() => {
  const type = form.type;
  if (txStore.categories && txStore.categories[type]) {
    return txStore.categories[type];
  }
  return [];
});

const getCategoryName = (id) => {
  if (!txStore.categories.all) return '...';
  const found = txStore.categories.all.find(c => c.id === id);
  return found ? found.name : '...';
};

const toggleEdit = () => {
  isEditing.value = !isEditing.value;
};

const submitUpdate = async () => {
  if (form.amount <= 0) return;
  isSubmitting.value = true;

  try {
    const payload = {
      category_id: form.category_id,
      type: form.type,
      amount: parseFloat(form.amount),
      date: form.date,
      description: form.description,
      currency: form.isZed ? form.currency : 'UAH',
      manual_rate: (form.isZed && form.manual_rate) ? parseFloat(form.manual_rate) : null,
      is_fop: form.type === 'income' ? form.is_fop : true
    };

    await txStore.editTransaction(props.transaction.transaction_id, props.userId, payload);
    isEditing.value = false;
    emit('updated');
  } catch (e) {
    console.error("Update error:", e);
  } finally {
    isSubmitting.value = false;
  }
};

const deleteTx = async () => {
  if (confirm('Ви впевнені, що хочете видалити цю транзакцію?')) {
    try {
      await txStore.deleteTransaction(props.transaction.transaction_id, props.userId);
      emit('deleted');
      emit('close');
    } catch (e) {
      console.error("Delete error:", e);
    }
  }
};

const close = () => {
  isEditing.value = false;
  emit('close');
};

const handleOpenCategory = () => {
  isCategoryModalOpen.value = true;
};

const submitNewCategory = async () => {
  // Auto-select the newly created category
  const list = txStore.categories[form.type] || [];
  if (list.length > 0) {
    form.category_id = list[list.length - 1].id;
  }
  isCategoryModalOpen.value = false;
};

const formatCurrency = (val) => {
  return new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(val);
};

</script>

<template>
  <BaseModal :isOpen="isOpen" :title="isEditing ? 'Редагувати транзакцію' : 'Деталі транзакції'" @close="close">
    <div v-if="transaction && !isEditing" class="space-y-6">
      <!-- Summary Header -->
      <div class="p-6 rounded-3xl bg-gray-50 border border-gray-100 flex flex-col items-center text-center">
        <div :class="['w-16 h-16 rounded-2xl flex items-center justify-center mb-4 shadow-sm', transaction.transaction_type === 'income' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600']">
          <component :is="transaction.transaction_type === 'income' ? ArrowDownLeft : ArrowUpRight" class="w-8 h-8" stroke-width="3" />
        </div>
        <div class="text-3xl font-black tracking-tight" :class="transaction.transaction_type === 'income' ? 'text-green-600' : 'text-gray-900'">
          {{ transaction.transaction_type === 'income' ? '+' : '-' }}
          {{ transaction.transaction_amount.toLocaleString() }} ₴
        </div>
        <div v-if="transaction.is_foreign_currency" class="text-sm font-bold text-gray-400 mt-1 uppercase tracking-widest">
          {{ transaction.amount_original }} {{ transaction.currency_code }} <span class="mx-1">•</span> {{ transaction.exchange_rate }}
        </div>
        <div class="mt-4 px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-wider" :class="transaction.transaction_type === 'income' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'">
          {{ getCategoryName(transaction.category_id) }}
        </div>
      </div>

      <!-- Details List -->
      <div class="space-y-4">
        <div class="flex items-center justify-between p-4 bg-white border border-gray-100 rounded-2xl">
          <div class="flex items-center gap-3 text-gray-500">
            <Calendar :size="18" />
            <span class="text-xs font-black uppercase tracking-widest">Дата</span>
          </div>
          <span class="font-bold text-gray-800">{{ new Date(transaction.transaction_date).toLocaleDateString('uk-UA') }}</span>
        </div>

        <!-- Account Type for Income -->
        <div v-if="transaction.transaction_type === 'income'" class="flex items-center justify-between p-4 bg-white border border-gray-100 rounded-2xl">
          <div class="flex items-center gap-3 text-gray-500">
            <component :is="transaction.is_fop !== false ? CreditCard : User" :size="18" />
            <span class="text-xs font-black uppercase tracking-widest">Тип рахунку</span>
          </div>
          <span class="font-bold" :class="transaction.is_fop !== false ? 'text-blue-600' : 'text-amber-600'">
            {{ transaction.is_fop !== false ? 'ФОП Карта' : 'Особистий' }}
          </span>
        </div>

        <div v-if="transaction.notes" class="p-4 bg-white border border-gray-100 rounded-2xl space-y-2">
          <div class="flex items-center gap-3 text-gray-500">
            <FileText :size="18" />
            <span class="text-xs font-black uppercase tracking-widest">Коментар</span>
          </div>
          <p class="text-gray-700 font-medium italic">"{{ transaction.notes }}"</p>
        </div>
      </div>

      <!-- Actions -->
      <div class="grid grid-cols-2 gap-4">
        <button 
          @click="toggleEdit"
          class="py-4 rounded-2xl font-black text-sm uppercase tracking-widest border-2 border-gray-100 text-gray-600 hover:bg-gray-50 transition-all flex items-center justify-center gap-2"
        >
          <Pencil :size="18" />
          Редагувати
        </button>
        <button 
          @click="deleteTx"
          class="py-4 rounded-2xl font-black text-sm uppercase tracking-widest border-2 border-red-50 text-red-500 hover:bg-red-50 transition-all flex items-center justify-center gap-2"
        >
          <Trash2 :size="18" />
          Видалити
        </button>
      </div>

      <button 
        @click="close"
        class="w-full py-4 rounded-2xl font-black text-sm uppercase tracking-widest bg-gray-900 text-white hover:bg-black transition-all shadow-lg active:scale-[0.98]"
      >
        Закрити
      </button>
    </div>

    <!-- Edit Mode -->
    <form v-else-if="transaction && isEditing" @submit.prevent="submitUpdate">
      <TransactionForm 
        v-model="form"
        :fopSettings="fopSettings"
        :isSubmitting="isSubmitting"
        @add-category="handleOpenCategory" 
      />
      
      <div class="mt-6">
        <button 
          @click="isEditing = false"
          type="button"
          class="w-full py-4 rounded-2xl font-black text-sm uppercase tracking-widest bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all"
        >
          Скасувати
        </button>
      </div>
    </form>
  </BaseModal>

  <!-- Reusable Category Creation Modal -->
  <CategoryModal 
    v-if="isCategoryModalOpen"
    :isOpen="isCategoryModalOpen"
    :userId="userId"
    :type="form.type"
    @close="isCategoryModalOpen = false"
    @saved="submitNewCategory"
  />
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
</style>
