<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ArrowLeft, ClipboardList, Database, RefreshCw, Save } from 'lucide-vue-next';
import { useTaxRulesStore } from '@/stores/taxRulesStore';
import { useNotificationStore } from '@/stores/notificationStore';

const router = useRouter();
const store = useTaxRulesStore();
const notify = useNotificationStore();

const selectedId = ref(null);
const seedYear = ref(new Date().getFullYear());
const saving = ref(false);

const EDIT_FIELDS = [
  { key: 'min_wage', label: 'МЗП', step: 0.01 },
  { key: 'esv_value', label: 'ЄСВ (міс)', step: 0.01 },
  { key: 'single_tax_g1', label: 'ЄП 1 гр', step: 0.01 },
  { key: 'single_tax_g2', label: 'ЄП 2 гр', step: 0.01 },
  { key: 'fixed_military_tax', label: 'ВЗ фікс (міс)', step: 0.01 },
  { key: 'limit_g1', label: 'Ліміт 1 гр', step: 1 },
  { key: 'limit_g2', label: 'Ліміт 2 гр', step: 1 },
  { key: 'limit_g3', label: 'Ліміт 3 гр', step: 1 },
  { key: 'limit_g1_mzp_units', label: 'МЗП од. 1 гр', step: 1, int: true },
  { key: 'limit_g2_mzp_units', label: 'МЗП од. 2 гр', step: 1, int: true },
  { key: 'limit_g3_mzp_units', label: 'МЗП од. 3 гр', step: 1, int: true },
  { key: 'income_tax_percent', label: 'ЄП 3 гр %', step: 0.01 },
  { key: 'income_tax_percent_vat', label: 'ЄП 3+ПДВ %', step: 0.01 },
  { key: 'military_tax_percent', label: 'ВЗ 3 гр %', step: 0.01 },
  { key: 'g4_rate_arable', label: 'Г4 рілля %', step: 0.01 },
  { key: 'g4_rate_water', label: 'Г4 вода %', step: 0.01 },
  { key: 'g4_rate_closed_soil', label: 'Г4 теплиця %', step: 0.01 },
  { key: 'vat_supply_threshold', label: 'Поріг ПДВ', step: 1 },
];

const draft = reactive({});

const selectedRow = computed(() =>
  store.adminList.find((r) => r.id === selectedId.value) ?? null
);

function loadDraft(row) {
  selectedId.value = row.id;
  for (const f of EDIT_FIELDS) {
    draft[f.key] = row[f.key];
  }
}

async function init() {
  await store.checkAdmin();
  if (!store.isAdmin) {
    notify.showError('Немає доступу до редагування податкових правил');
    router.replace('/settings');
    return;
  }
  await store.fetchAdminList();
  if (store.adminList.length) loadDraft(store.adminList[0]);
}

onMounted(init);

async function save() {
  if (!selectedId.value) return;
  saving.value = true;
  try {
    const payload = {};
    for (const f of EDIT_FIELDS) {
      const v = draft[f.key];
      payload[f.key] = f.int ? parseInt(v, 10) : parseFloat(v);
    }
    await store.updateRule(selectedId.value, payload);
    notify.showSuccess('Правила збережено');
  } catch (e) {
    const msg = e.response?.data?.detail || 'Помилка збереження';
    notify.showError(typeof msg === 'string' ? msg : 'Помилка збереження');
  } finally {
    saving.value = false;
  }
}

async function runSeed() {
  try {
    await store.seedYear(seedYear.value);
    notify.showSuccess(`Оновлено періоди за ${seedYear.value} рік`);
    if (store.adminList.length) loadDraft(store.adminList[0]);
  } catch (e) {
    notify.showError('Не вдалося заповнити рік');
  }
}

function periodLabel(row) {
  return `${row.year} · ${String(row.month).padStart(2, '0')}`;
}
</script>

<template>
  <div class="max-w-6xl mx-auto p-4 sm:p-8 pb-24 font-sans">
    <button
      type="button"
      class="flex items-center gap-2 text-gray-500 font-bold hover:text-gray-800 mb-6"
      @click="router.push('/settings')"
    >
      <ArrowLeft :size="20" />
      Налаштування
    </button>

    <header class="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div class="flex items-start gap-4">
        <div class="w-14 h-14 rounded-2xl bg-slate-800 text-white flex items-center justify-center">
          <Database :size="28" />
        </div>
        <div>
          <h1 class="text-3xl font-black text-gray-900">Податкові правила</h1>
          <p class="text-gray-500 font-medium mt-1">
            Єдине джерело для квізу, розрахунків і GET /tax/rules
          </p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-50 font-bold text-indigo-800 hover:bg-indigo-100"
          @click="router.push({ name: 'admin-quiz-rules' })"
        >
          <ClipboardList :size="18" />
          Правила квізу
        </button>
        <input
          v-model.number="seedYear"
          type="number"
          min="2020"
          max="2100"
          class="w-24 px-3 py-2 rounded-xl border-2 border-gray-100 font-bold"
        >
        <button
          type="button"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-100 font-bold text-gray-800 hover:bg-gray-200"
          @click="runSeed"
        >
          <RefreshCw :size="18" />
          Seed року
        </button>
      </div>
    </header>

    <div v-if="store.adminLoading" class="text-gray-500 font-medium">Завантаження…</div>

    <div v-else class="grid lg:grid-cols-[280px_1fr] gap-6">
      <aside class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden max-h-[70vh] overflow-y-auto">
        <button
          v-for="row in store.adminList"
          :key="row.id"
          type="button"
          class="w-full text-left px-4 py-3 border-b border-gray-50 font-bold transition-colors"
          :class="selectedId === row.id ? 'bg-blue-50 text-blue-800' : 'text-gray-700 hover:bg-gray-50'"
          @click="loadDraft(row)"
        >
          {{ periodLabel(row) }}
        </button>
      </aside>

      <section v-if="selectedRow" class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 class="text-lg font-black text-gray-900 mb-4">
          Редагування: {{ periodLabel(selectedRow) }}
        </h2>

        <div class="grid sm:grid-cols-2 gap-4">
          <label
            v-for="f in EDIT_FIELDS"
            :key="f.key"
            class="block"
          >
            <span class="text-xs font-black text-gray-400 uppercase tracking-widest">{{ f.label }}</span>
            <input
              v-model.number="draft[f.key]"
              type="number"
              :step="f.step"
              class="mt-1 w-full px-4 py-3 rounded-xl border-2 border-gray-100 font-bold focus:border-blue-500 outline-none"
            >
          </label>
        </div>

        <button
          type="button"
          class="mt-6 inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-blue-600 text-white font-black hover:bg-blue-700 disabled:opacity-50"
          :disabled="saving"
          @click="save"
        >
          <Save :size="18" />
          {{ saving ? 'Збереження…' : 'Зберегти період' }}
        </button>
      </section>
    </div>
  </div>
</template>
