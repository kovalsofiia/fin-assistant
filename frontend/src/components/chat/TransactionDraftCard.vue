<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { Check, X } from 'lucide-vue-next';
import api from '@/services/api';
import { useTransactionStore } from '@/stores/transactionStore';

const props = defineProps({
    // {type, amount, currency, date, category_id, category_name, category_hint, description, is_fop} — з backend/agent/drafts.py
    draft: { type: Object, required: true },
});

const txStore = useTransactionStore();
const form = reactive({
    type: props.draft.type,
    amount: props.draft.amount,
    date: props.draft.date,
    category_id: props.draft.category_id || '',
    description: props.draft.description || '',
});
const status = ref('editing'); // editing | saving | saved | cancelled
const error = ref('');
const today = new Date().toLocaleDateString('sv-SE'); // YYYY-MM-DD у локальному часовому поясі

const categories = computed(() => txStore.categories?.[form.type] || []);
const isEditable = computed(() => status.value === 'editing');
const canSave = computed(() => isEditable.value && Number(form.amount) > 0 && Boolean(form.date) && Boolean(form.type));

onMounted(async () => {
    if (!txStore.categories?.all?.length) {
        try {
            await txStore.fetchCategories();
        } catch {
            // Без категорій транзакцію все одно можна додати «Без категорії»
        }
    }
});

function onTypeChange() {
    // Категорії доходів і витрат різні — скидаємо вибір, якщо він не підходить до нового типу
    if (!categories.value.some((c) => c.id === form.category_id)) form.category_id = '';
}

async function save() {
    if (!canSave.value) return;
    status.value = 'saving';
    error.value = '';
    try {
        await api.createTransaction({
            type: form.type,
            amount: Number(form.amount),
            date: form.date,
            category_id: form.category_id || null,
            description: form.description.trim() || null,
            currency: 'UAH',
            is_fop: props.draft.is_fop,
        });
    } catch (e) {
        status.value = 'editing';
        const detail = e?.response?.data?.detail;
        error.value = typeof detail === 'string' ? detail : 'Не вдалося додати транзакцію.';
        return;
    }
    status.value = 'saved';
    // Оновлюємо дашборд окремо: помилка оновлення не означає, що запис не додано
    txStore.fetchTransactions().catch(() => {});
}

function cancel() {
    status.value = 'cancelled';
}
</script>

<template>
  <div class="rounded-xl bg-white p-3 text-sm ring-1 ring-gray-200">
    <p class="mb-2 font-medium text-gray-900">Нова транзакція</p>

    <div class="grid grid-cols-2 gap-2">
      <select
        v-model="form.type"
        :disabled="!isEditable"
        aria-label="Тип"
        class="rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
        @change="onTypeChange"
      >
        <option value="expense">Витрата</option>
        <option value="income">Дохід</option>
      </select>
      <input
        v-model="form.amount"
        type="number"
        min="0.01"
        step="0.01"
        :disabled="!isEditable"
        aria-label="Сума, грн"
        placeholder="Сума, грн"
        class="rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
      />
      <input
        v-model="form.date"
        type="date"
        :max="today"
        :disabled="!isEditable"
        aria-label="Дата"
        class="rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
      />
      <select
        v-model="form.category_id"
        :disabled="!isEditable"
        aria-label="Категорія"
        class="rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
      >
        <option value="">Без категорії</option>
        <option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option>
      </select>
      <input
        v-model="form.description"
        maxlength="255"
        :disabled="!isEditable"
        aria-label="Опис"
        placeholder="Опис"
        class="col-span-2 rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
      />
    </div>

    <p v-if="draft.category_hint && !form.category_id" class="mt-1 text-xs text-amber-700">
      Категорію «{{ draft.category_hint }}» не знайдено — оберіть її зі списку.
    </p>
    <p v-if="error" class="mt-2 text-xs text-red-600">{{ error }}</p>

    <div v-if="status === 'editing' || status === 'saving'" class="mt-3 flex justify-end gap-2">
      <button
        type="button"
        :disabled="status === 'saving'"
        class="rounded-lg px-3 py-1.5 text-gray-600 hover:bg-gray-100 disabled:opacity-40"
        @click="cancel"
      >
        Скасувати
      </button>
      <button
        type="button"
        :disabled="!canSave"
        class="rounded-lg bg-blue-600 px-3 py-1.5 font-medium text-white disabled:opacity-40"
        @click="save"
      >
        {{ status === 'saving' ? 'Додаю…' : 'Додати' }}
      </button>
    </div>
    <p v-else-if="status === 'saved'" class="mt-3 flex items-center gap-1 text-green-700">
      <Check class="h-4 w-4" aria-hidden="true" /> Додано
    </p>
    <p v-else class="mt-3 flex items-center gap-1 text-gray-500">
      <X class="h-4 w-4" aria-hidden="true" /> Скасовано
    </p>
  </div>
</template>
