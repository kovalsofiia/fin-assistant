<script setup>
import { ref } from 'vue';
import api from '@/services/api';
import { downloadCsvResponse } from '@/utils/downloadCsv';
import { Download, FileSpreadsheet } from 'lucide-vue-next';

const props = defineProps({
  startDate: { type: String, default: '' },
  endDate: { type: String, default: '' },
  year: { type: Number, default: () => new Date().getFullYear() },
});

const exporting = ref(null);

const runExport = async (type) => {
  exporting.value = type;
  try {
    const params = {};
    if (type === 'transactions' || type === 'report') {
      if (!props.startDate || !props.endDate) {
        alert('Оберіть період (дати початку та кінця) у фільтрах.');
        return;
      }
      params.start_date = props.startDate;
      params.end_date = props.endDate;
    }
    if (type === 'tax_history') {
      params.year = props.year;
    }
    const res = await api.exportCsv(type, params);
    downloadCsvResponse(res, `fop_${type}.csv`);
  } catch (e) {
    console.error('CSV export failed:', e);
  } finally {
    exporting.value = null;
  }
};

const buttons = [
  { id: 'transactions', label: 'Транзакції', hint: 'Усі операції за період' },
  { id: 'report', label: 'Фінансовий звіт', hint: 'Підсумки та категорії' },
  { id: 'tax_history', label: 'Історія податків', hint: 'Збережені нарахування' },
];
</script>

<template>
  <div class="bg-white rounded-[2rem] border border-gray-100 shadow-xl shadow-gray-200/40 p-6 sm:p-8">
    <div class="flex items-center gap-3 mb-2">
      <FileSpreadsheet class="w-6 h-6 text-emerald-600" />
      <h3 class="text-lg font-black text-gray-900">Експорт CSV</h3>
    </div>
    <p class="text-sm text-gray-500 mb-5">
      Завантаження даних для планування звітності та аналізу в Excel / Google Sheets.
    </p>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <button
        v-for="btn in buttons"
        :key="btn.id"
        type="button"
        class="text-left p-4 rounded-2xl border border-gray-100 hover:border-emerald-200 hover:bg-emerald-50/50 transition-all disabled:opacity-50"
        :disabled="exporting !== null"
        @click="runExport(btn.id)"
      >
        <span class="flex items-center gap-2 font-bold text-gray-800 text-sm">
          <Download class="w-4 h-4 text-emerald-600" />
          {{ exporting === btn.id ? 'Експорт…' : btn.label }}
        </span>
        <span class="block text-xs text-gray-400 mt-1">{{ btn.hint }}</span>
      </button>
    </div>
  </div>
</template>
