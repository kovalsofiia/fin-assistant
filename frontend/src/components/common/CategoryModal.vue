<script setup>
import { ref, watch } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { useNotificationStore } from '@/stores/notificationStore';
import BaseModal from '@/components/common/BaseModal.vue';

const props = defineProps({
  isOpen: Boolean,
  userId: String,
  type: {
    type: String,
    default: 'expense'
  },
  category: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'saved']);

const txStore = useTransactionStore();
const notificationStore = useNotificationStore();

const catName = ref('');
const isSubmitting = ref(false);

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    if (props.category) {
      catName.value = props.category.name;
    } else {
      catName.value = '';
    }
  }
});

const submit = async () => {
  if (!catName.value.trim() || !props.userId) return;
  isSubmitting.value = true;
  
  try {
    if (props.category) {
      // Edit mode
      await txStore.modifyCategory(props.category.id, props.userId, {
        name: catName.value
      });
      notificationStore.showSuccess("Категорію оновлено");
    } else {
      // Create mode
      await txStore.createNewCategory({
        name: catName.value,
        type: props.type,
        user_id: props.userId
      });
      notificationStore.showSuccess("Категорію створено");
    }
    
    emit('saved', catName.value);
    emit('close');
  } catch (e) {
    console.error("Category save error:", e);
    notificationStore.showError(e.response?.data?.detail || "Помилка при збереженні категорії");
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <BaseModal 
    :isOpen="isOpen" 
    :title="category ? 'Редагувати категорію' : 'Нова категорія'" 
    @close="$emit('close')"
  >
    <div class="space-y-8">
      <div class="p-6 bg-gray-50 rounded-3xl border border-gray-100">
         <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Тип операції</p>
         <p class="font-black text-xl" :class="type === 'income' ? 'text-green-600' : 'text-red-600'">
           {{ type === 'income' ? 'Дохід' : 'Витрата' }}
         </p>
      </div>
      
      <div class="space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Назва категорії</label>
        <input 
          type="text" 
          v-model="catName" 
          placeholder="Напр. Фріланс" 
          autofocus 
          @keyup.enter="submit"
          class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-black text-gray-800"
        >
      </div>

      <button 
        @click="submit"
        :disabled="isSubmitting"
        class="w-full py-5 rounded-3xl font-black bg-gray-900 text-white hover:bg-black transition-all shadow-xl shadow-gray-200 active:scale-[0.98] disabled:opacity-50"
      >
        {{ isSubmitting ? 'Збереження...' : (category ? 'Зберегти зміни' : 'Створити категорію') }}
      </button>
    </div>
  </BaseModal>
</template>
