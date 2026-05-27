<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ArrowLeft, ClipboardList, Filter } from 'lucide-vue-next';
import {
  FOP_GROUP_QUIZ_RULES_CATALOG,
  QUIZ_RULE_TYPE_LABELS,
  filterQuizRulesCatalog,
} from '@/constants/fopGroupQuizRulesCatalog';
import { useTaxRulesStore } from '@/stores/taxRulesStore';
import { useNotificationStore } from '@/stores/notificationStore';

const router = useRouter();
const taxRulesStore = useTaxRulesStore();
const notify = useNotificationStore();

const typeFilter = ref('');
const groupFilter = ref('');

const filteredRules = computed(() => {
  const gf = groupFilter.value;
  const groupArg = gf === '' ? null : gf === 'all' ? 'all' : Number(gf);
  return filterQuizRulesCatalog(typeFilter.value || null, groupArg);
});

const typeBadgeClass = {
  questions: 'bg-sky-100 text-sky-900',
  eligibility: 'bg-amber-100 text-amber-900',
  recommendation: 'bg-emerald-100 text-emerald-900',
  tax: 'bg-slate-100 text-slate-800',
  pathing: 'bg-violet-100 text-violet-900',
};

function typeLabel(type) {
  return QUIZ_RULE_TYPE_LABELS.find((t) => t.id === type)?.label ?? type;
}

onMounted(async () => {
  await taxRulesStore.checkAdmin();
  if (!taxRulesStore.isAdmin) {
    notify.showError('Немає доступу');
    router.replace('/settings');
  }
});
</script>

<template>
  <div class="max-w-6xl mx-auto p-4 sm:p-8 pb-24 font-sans">
    <button
      type="button"
      class="flex items-center gap-2 text-gray-500 font-bold hover:text-gray-800 mb-6"
      @click="router.push({ name: 'admin-tax-rules' })"
    >
      <ArrowLeft :size="20" />
      Податкові правила
    </button>

    <header class="mb-8 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
      <div class="flex items-start gap-4">
        <div class="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center">
          <ClipboardList :size="28" />
        </div>
        <div>
          <h1 class="text-3xl font-black text-gray-900">Правила квізу ФОП</h1>
          <p class="text-gray-500 font-medium mt-1 max-w-xl">
            Довідник логіки допустимості, Pathing і рекомендації. Числові параметри — у
            <button type="button" class="text-indigo-600 font-bold hover:underline" @click="router.push({ name: 'admin-tax-rules' })">
              податкових правилах
            </button>.
            Код: <code class="text-xs bg-gray-100 px-1 rounded">fopGroupQuizEngine.js</code>
          </p>
        </div>
      </div>
      <p class="text-sm font-bold text-gray-400">
        Всього правил: {{ FOP_GROUP_QUIZ_RULES_CATALOG.length }}
      </p>
    </header>

    <div class="flex flex-wrap items-center gap-3 mb-6 p-4 rounded-2xl bg-gray-50 border border-gray-100">
      <Filter :size="18" class="text-gray-400 shrink-0" />
      <select
        v-model="typeFilter"
        class="px-4 py-2 rounded-xl border-2 border-gray-100 font-bold text-sm bg-white"
      >
        <option value="">Усі типи</option>
        <option v-for="t in QUIZ_RULE_TYPE_LABELS" :key="t.id" :value="t.id">{{ t.label }}</option>
      </select>
      <select
        v-model="groupFilter"
        class="px-4 py-2 rounded-xl border-2 border-gray-100 font-bold text-sm bg-white"
      >
        <option value="">Усі групи</option>
        <option value="all">Загальні</option>
        <option v-for="g in [1, 2, 3, 4]" :key="g" :value="String(g)">Група {{ g }}</option>
      </select>
    </div>

    <div class="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-x-auto">
      <table class="w-full text-left text-sm min-w-[720px]">
        <thead class="bg-gray-50 text-xs font-black uppercase tracking-wider text-gray-400">
          <tr>
            <th class="px-4 py-3 w-24">Група</th>
            <th class="px-4 py-3 w-32">Тип</th>
            <th class="px-4 py-3">Умова</th>
            <th class="px-4 py-3">Наслідок</th>
            <th class="px-4 py-3 w-48">Примітка</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-for="row in filteredRules" :key="row.id" class="hover:bg-gray-50/80 align-top">
            <td class="px-4 py-3 font-black text-gray-900">
              {{ row.group === 'all' ? '—' : row.group }}
            </td>
            <td class="px-4 py-3">
              <span
                class="inline-block px-2 py-1 rounded-lg text-xs font-black"
                :class="typeBadgeClass[row.type] ?? 'bg-gray-100'"
              >
                {{ typeLabel(row.type) }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-800 font-medium">{{ row.condition }}</td>
            <td class="px-4 py-3 text-gray-700">{{ row.effect }}</td>
            <td class="px-4 py-3 text-xs text-gray-500">{{ row.note ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!filteredRules.length" class="p-8 text-center text-gray-500 font-medium">
        Немає правил за обраними фільтрами
      </p>
    </div>
  </div>
</template>
