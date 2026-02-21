<script setup>
import { ref } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { Tag, Trash2, Edit2, Plus } from 'lucide-vue-next';
import CategoryModal from '@/components/common/CategoryModal.vue';

const props = defineProps({
  userId: {
    type: String,
    required: true
  }
});

const notificationStore = useNotificationStore();
const txStore = useTransactionStore();

// --- Category Management Logic ---
const isModalOpen = ref(false);
const selectedCategory = ref(null);
const modalType = ref('expense');

const startEditCategory = (cat) => {
  selectedCategory.value = cat;
  modalType.value = cat.type;
  isModalOpen.value = true;
};

const handleAddCategory = (type) => {
  selectedCategory.value = null;
  modalType.value = type;
  isModalOpen.value = true;
};

const handleDeleteCategory = async (cat) => {
  if (cat.name === 'None') {
    notificationStore.showError("Категорію 'None' не можна видалити");
    return;
  }
  if (confirm(`Видалити категорію "${cat.name}"? Усі транзакції цієї категорії будуть перенесені до "None".`)) {
    try {
      await txStore.removeCategory(cat.id, props.userId);
      notificationStore.showSuccess("Категорію видалено");
    } catch (e) {
      notificationStore.showError(e.response?.data?.detail || "Помилка при видаленні");
    }
  }
};
</script>

<template>
  <section class="bg-white rounded-[2rem] sm:rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-8">
    <div class="flex items-center gap-4 mb-8">
      <div class="bg-amber-500 p-3 rounded-2xl text-white shadow-lg shadow-amber-200">
        <Tag :size="24" stroke-width="2.5" />
      </div>
      <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1">Керуйте власними категоріями</p>
    </div>

    <div class="space-y-8">
      
      <!-- Income Categories -->
        <div class="flex justify-between items-center mb-4 px-2">
          <h3 class="text-xs font-black text-gray-400 uppercase tracking-widest">Категорії доходів</h3>
          <button @click="handleAddCategory('income')" class="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:underline">+ Додати</button>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div 
            v-for="cat in txStore.categories.income.filter(c => c.user_id)" 
            :key="cat.id"
            class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-100 group transition-all hover:bg-white hover:shadow-md"
          >
            <span class="font-bold text-gray-700">{{ cat.name }}</span>
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                v-if="cat.name !== 'None'"
                @click="startEditCategory(cat)" 
                class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all"
              >
                <Edit2 :size="16" />
              </button>
              <button 
                v-if="cat.name !== 'None'"
                @click="handleDeleteCategory(cat)" 
                class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </div>

      <!-- Expense Categories -->
        <div class="flex justify-between items-center mb-4 px-2">
          <h3 class="text-xs font-black text-gray-400 uppercase tracking-widest">Категорії витрат</h3>
          <button @click="handleAddCategory('expense')" class="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:underline">+ Додати</button>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div 
            v-for="cat in txStore.categories.expense.filter(c => c.user_id)" 
            :key="cat.id"
            class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-100 group transition-all hover:bg-white hover:shadow-md"
          >
            <span class="font-bold text-gray-700">{{ cat.name }}</span>
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                v-if="cat.name !== 'None'"
                @click="startEditCategory(cat)" 
                class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all"
              >
                <Edit2 :size="16" />
              </button>
              <button 
                v-if="cat.name !== 'None'"
                @click="handleDeleteCategory(cat)" 
                class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </div>

      <div v-if="!txStore.categories.all?.some(c => c.user_id)" class="py-12 text-center bg-gray-50/50 rounded-3xl border-2 border-dashed border-gray-100">
        <Tag :size="32" class="mx-auto text-gray-300 mb-3" />
        <p class="text-sm font-bold text-gray-400 uppercase tracking-widest">У вас ще немає власних категорій</p>
        <div class="flex justify-center gap-4 mt-4">
          <button @click="handleAddCategory('income')" class="text-[10px] font-black bg-white border border-gray-200 px-4 py-2 rounded-xl hover:border-blue-500 transition-all text-gray-600 capitalize">+ Дохід</button>
          <button @click="handleAddCategory('expense')" class="text-[10px] font-black bg-white border border-gray-200 px-4 py-2 rounded-xl hover:border-blue-500 transition-all text-gray-600 capitalize">+ Витрата</button>
        </div>
      </div>
    </div>

    <!-- Standalone Category Modal -->
    <CategoryModal 
      v-if="isModalOpen"
      :isOpen="isModalOpen"
      :userId="userId"
      :type="modalType"
      :category="selectedCategory"
      @close="isModalOpen = false; selectedCategory = null"
    />
  </section>
</template>
