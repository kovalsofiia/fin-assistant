<script setup>
import { ref } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { Tag, Trash2, Edit2, Plus, Check, X } from 'lucide-vue-next';

const props = defineProps({
  userId: {
    type: String,
    required: true
  }
});

const notificationStore = useNotificationStore();
const txStore = useTransactionStore();

// --- Category Management Logic ---
const editingCatId = ref(null);
const editingCatName = ref('');

const startEditCategory = (cat) => {
  editingCatId.value = cat.id;
  editingCatName.value = cat.name;
};

const cancelEditCategory = () => {
  editingCatId.value = null;
  editingCatName.value = '';
};

const handleUpdateCategory = async (cat) => {
  if (!editingCatName.value.trim() || editingCatName.value === cat.name) {
    cancelEditCategory();
    return;
  }
  try {
    await txStore.modifyCategory(cat.id, props.userId, { name: editingCatName.value });
    notificationStore.showSuccess("Категорію оновлено");
    cancelEditCategory();
  } catch (e) {
    notificationStore.showError("Помилка при оновленні");
  }
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

const newCatName = ref('');
const newCatType = ref('expense');
const isAddingCategory = ref(false);

const handleAddCategory = async () => {
  if (!newCatName.value.trim()) return;
  try {
    await txStore.createNewCategory({
      name: newCatName.value,
      type: newCatType.value,
      user_id: props.userId
    });
    notificationStore.showSuccess("Категорію створено");
    newCatName.value = '';
    isAddingCategory.value = false;
  } catch (e) {
    notificationStore.showError("Помилка при створенні");
  }
};
</script>

<template>
  <section class="bg-white rounded-[2rem] sm:rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-8">
    <div class="flex items-center gap-4 mb-8">
      <div class="bg-amber-500 p-3 rounded-2xl text-white shadow-lg shadow-amber-200">
        <Tag :size="24" stroke-width="2.5" />
      </div>
      <h2 class="text-2xl font-black text-gray-900">Категорії</h2>
      <button 
        type="button" 
        @click="isAddingCategory = !isAddingCategory" 
        class="ml-auto text-xs font-black bg-gray-900 text-white px-4 py-2 rounded-xl hover:bg-black transition-all flex items-center gap-2"
      >
        <Plus :size="16" stroke-width="3" />
        Додати
      </button>
    </div>

    <div class="space-y-8">
      <!-- Add New Category Form -->
      <transition enter-active-class="transition duration-300 ease-out" enter-from-class="opacity-0 -translate-y-4" enter-to-class="opacity-100 translate-y-0">
        <div v-if="isAddingCategory" class="p-6 bg-amber-50 rounded-3xl border border-amber-100 shadow-inner space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-[10px] font-black text-amber-700 uppercase tracking-widest px-2">Назва</label>
              <input type="text" v-model="newCatName" placeholder="Напр. Долари" class="w-full px-5 py-3 bg-white border-2 border-transparent focus:border-amber-500 rounded-2xl outline-none font-bold text-gray-800">
            </div>
            <div class="space-y-2">
              <label class="text-[10px] font-black text-amber-700 uppercase tracking-widest px-2">Тип</label>
              <select v-model="newCatType" class="w-full px-5 py-3 bg-white border-2 border-transparent focus:border-amber-500 rounded-2xl outline-none font-bold text-gray-800">
                <option value="income">Дохід</option>
                <option value="expense">Витрата</option>
              </select>
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button @click="isAddingCategory = false" type="button" class="px-6 py-3 font-bold text-amber-700 hover:bg-amber-100/50 rounded-xl transition-all">Скасувати</button>
            <button @click="handleAddCategory" type="button" class="px-8 py-3 bg-amber-600 text-white font-black rounded-xl hover:bg-amber-700 transition-all shadow-lg shadow-amber-200">Створити</button>
          </div>
        </div>
      </transition>
      
      <!-- Income Categories -->
      <div v-if="txStore.categories.income?.length > 0">
        <h3 class="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 px-2">Категорії доходів</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div 
            v-for="cat in txStore.categories.income.filter(c => c.user_id)" 
            :key="cat.id"
            class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-100 group transition-all hover:bg-white hover:shadow-md"
          >
            <div v-if="editingCatId === cat.id" class="flex-grow flex items-center gap-2">
              <input 
                type="text" 
                v-model="editingCatName" 
                class="flex-grow px-3 py-2 bg-white border-2 border-amber-500 rounded-xl outline-none font-bold text-sm"
                @keyup.enter="handleUpdateCategory(cat)"
                @keyup.esc="cancelEditCategory"
                autoFocus
              >
              <button @click="handleUpdateCategory(cat)" class="p-2 text-green-600 hover:bg-green-50 rounded-lg">
                <Check :size="18" stroke-width="3" />
              </button>
              <button @click="cancelEditCategory" class="p-2 text-gray-400 hover:bg-gray-100 rounded-lg">
                <X :size="18" />
              </button>
            </div>
            <template v-else>
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
            </template>
          </div>
        </div>
      </div>

      <!-- Expense Categories -->
      <div v-if="txStore.categories.expense?.length > 0">
        <h3 class="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 px-2">Категорії витрат</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div 
            v-for="cat in txStore.categories.expense.filter(c => c.user_id)" 
            :key="cat.id"
            class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-100 group transition-all hover:bg-white hover:shadow-md"
          >
            <div v-if="editingCatId === cat.id" class="flex-grow flex items-center gap-2">
              <input 
                type="text" 
                v-model="editingCatName" 
                class="flex-grow px-3 py-2 bg-white border-2 border-amber-500 rounded-xl outline-none font-bold text-sm"
                @keyup.enter="handleUpdateCategory(cat)"
                @keyup.esc="cancelEditCategory"
                autoFocus
              >
              <button @click="handleUpdateCategory(cat)" class="p-2 text-green-600 hover:bg-green-50 rounded-lg">
                <Check :size="18" stroke-width="3" />
              </button>
              <button @click="cancelEditCategory" class="p-2 text-gray-400 hover:bg-gray-100 rounded-lg">
                <X :size="18" />
              </button>
            </div>
            <template v-else>
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
            </template>
          </div>
        </div>
      </div>

      <div v-if="!txStore.categories.all?.some(c => c.user_id)" class="py-12 text-center bg-gray-50 rounded-3xl border-2 border-dashed border-gray-100">
        <Tag :size="32" class="mx-auto text-gray-300 mb-3" />
        <p class="text-sm font-bold text-gray-400 uppercase tracking-widest">У вас ще немає власних категорій</p>
        <p class="text-xs text-gray-400 mt-1">Ви можете створити їх при додаванні транзакції</p>
      </div>
    </div>
  </section>
</template>
