<script setup>
import { ref, onMounted } from 'vue';
import { useAccountStore } from '@/stores/accountStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { Wallet, Plus, Edit2, Trash2 } from 'lucide-vue-next';
import AccountModal from '@/components/common/AccountModal.vue';

const accountStore = useAccountStore();
const notificationStore = useNotificationStore();

const isModalOpen = ref(false);
const selectedAccount = ref(null);

onMounted(() => {
  accountStore.fetchAccounts();
});

const openCreate = () => {
  selectedAccount.value = null;
  isModalOpen.value = true;
};

const openEdit = (account) => {
  selectedAccount.value = account;
  isModalOpen.value = true;
};

const handleSave = async (payload) => {
  try {
    if (selectedAccount.value) {
      await accountStore.updateAccount(selectedAccount.value.id, payload);
      notificationStore.showSuccess('Рахунок оновлено');
    } else {
      await accountStore.createAccount(payload);
      notificationStore.showSuccess('Рахунок створено');
    }
    isModalOpen.value = false;
  } catch (e) {
    notificationStore.showError(e.response?.data?.detail || 'Помилка збереження');
  }
};

const handleDelete = async (account) => {
  if (
    !confirm(
      `Видалити рахунок «${account.name}»? Транзакції залишаться, але без прив’язки до цього рахунку.`
    )
  ) {
    return;
  }
  try {
    await accountStore.removeAccount(account.id);
    notificationStore.showSuccess('Рахунок видалено');
  } catch (e) {
    notificationStore.showError(e.response?.data?.detail || 'Помиля видалення');
  }
};
</script>

<template>
  <section class="bg-white rounded-[2rem] sm:rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-8">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
      <div class="flex items-center gap-4">
        <div class="bg-emerald-500 p-3 rounded-2xl text-white shadow-lg shadow-emerald-200">
          <Wallet :size="24" stroke-width="2.5" />
        </div>
        <div>
          <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1">
            Рахунки та картки
          </p>
          <p class="text-sm font-bold text-gray-600">Бізнес (ФОП) та особисті</p>
        </div>
      </div>
      <button
        type="button"
        class="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-emerald-600 text-white font-black text-sm hover:bg-emerald-700 transition-all"
        @click="openCreate"
      >
        <Plus :size="18" stroke-width="2.5" />
        Додати рахунок
      </button>
    </div>

    <p v-if="accountStore.error" class="mb-4 text-sm font-bold text-amber-700 bg-amber-50 border border-amber-100 rounded-2xl p-4">
      {{ accountStore.error }}
    </p>

    <div v-if="accountStore.isLoading" class="py-8 text-center text-gray-400 font-bold text-xs uppercase tracking-widest">
      Завантаження...
    </div>

    <div v-else-if="accountStore.accounts.length === 0" class="py-8 text-center text-gray-400 font-medium">
      Немає рахунків. Додайте перший або виконайте міграцію БД.
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div
        v-for="acc in accountStore.accounts"
        :key="acc.id"
        class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-100 group transition-all hover:bg-white hover:shadow-md"
      >
        <div class="min-w-0">
          <span class="font-bold text-gray-800 block truncate">{{ acc.name }}</span>
          <span v-if="acc.bank_name" class="text-xs text-gray-500 block truncate">{{ acc.bank_name }}</span>
          <div class="flex flex-wrap items-center gap-2 mt-2">
            <span
              class="px-1.5 py-0.5 rounded-md text-[9px] font-black uppercase tracking-tighter"
              :class="acc.is_business ? 'bg-blue-100 text-blue-600' : 'bg-amber-100 text-amber-600'"
            >
              {{ acc.is_business ? 'ФОП' : 'Особистий' }}
            </span>
            <span class="px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded-md text-[9px] font-black uppercase">
              {{ acc.currency_code }}
            </span>
          </div>
        </div>
        <div class="flex items-center gap-1 shrink-0 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
          <button
            type="button"
            class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all"
            @click="openEdit(acc)"
          >
            <Edit2 :size="16" />
          </button>
          <button
            type="button"
            class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"
            @click="handleDelete(acc)"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </div>
    </div>

    <AccountModal
      :isOpen="isModalOpen"
      :account="selectedAccount"
      @close="isModalOpen = false"
      @save="handleSave"
    />
  </section>
</template>
