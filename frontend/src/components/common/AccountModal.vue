<script setup>
import { ref, watch } from 'vue';
import BaseModal from '@/components/common/BaseModal.vue';

const props = defineProps({
  isOpen: Boolean,
  account: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['close', 'save']);

const name = ref('');
const bankName = ref('');
const currencyCode = ref('UAH');
const isBusiness = ref(true);

watch(
  () => [props.isOpen, props.account],
  () => {
    if (!props.isOpen) return;
    name.value = props.account?.name || '';
    bankName.value = props.account?.bank_name || '';
    currencyCode.value = props.account?.currency_code || 'UAH';
    isBusiness.value = props.account?.is_business !== false;
  },
  { immediate: true }
);

const submit = () => {
  if (!name.value.trim()) return;
  emit('save', {
    name: name.value.trim(),
    bank_name: bankName.value.trim() || null,
    currency_code: currencyCode.value,
    is_business: isBusiness.value,
  });
};
</script>

<template>
  <BaseModal
    :isOpen="isOpen"
    :title="account ? 'Редагувати рахунок' : 'Новий рахунок'"
    @close="$emit('close')"
  >
    <form class="space-y-6" @submit.prevent="submit">
      <div class="space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Назва</label>
        <input
          v-model="name"
          required
          maxlength="100"
          placeholder="Напр. Monobank ФОП"
          class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none font-bold text-gray-800"
        />
      </div>

      <div class="space-y-2">
        <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Банк (необов’язково)</label>
        <input
          v-model="bankName"
          maxlength="100"
          placeholder="ПриватБанк"
          class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none font-bold text-gray-800"
        />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="space-y-2">
          <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Валюта рахунку</label>
          <select
            v-model="currencyCode"
            class="w-full px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 rounded-2xl outline-none font-bold text-gray-800"
          >
            <option value="UAH">UAH (₴)</option>
            <option value="USD">USD ($)</option>
            <option value="EUR">EUR (€)</option>
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-xs font-black text-gray-400 uppercase tracking-widest px-1">Тип</label>
          <div class="flex p-1.5 bg-gray-100 rounded-2xl gap-2 h-[58px] items-center">
            <button
              type="button"
              class="flex-1 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all"
              :class="isBusiness ? 'bg-white shadow-sm text-blue-600' : 'text-gray-400'"
              @click.prevent="isBusiness = true"
            >
              ФОП
            </button>
            <button
              type="button"
              class="flex-1 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all"
              :class="!isBusiness ? 'bg-white shadow-sm text-amber-600' : 'text-gray-400'"
              @click.prevent="isBusiness = false"
            >
              Особистий
            </button>
          </div>
        </div>
      </div>

      <button
        type="submit"
        class="w-full py-4 rounded-2xl font-black bg-blue-600 text-white hover:bg-blue-700 transition-all"
      >
        Зберегти
      </button>
    </form>
  </BaseModal>
</template>
