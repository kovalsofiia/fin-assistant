<script setup>
import { ref, computed, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import api from '@/services/api';
import { supabase } from '@/services/supabase';
import { useNotificationStore } from '@/stores/notificationStore';
import {
  getStoredKveds,
  setStoredKveds,
  toKvedSyncPayload,
} from '@/utils/kvedStorage';
import {
  ClipboardList,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  BookOpen,
} from 'lucide-vue-next';

const props = defineProps({
  startDate: { type: String, default: '' },
  endDate: { type: String, default: '' },
});

const notificationStore = useNotificationStore();

const loading = ref(false);
const result = ref(null);
const error = ref(null);
const b2bOverride = ref(null);
const kvedChecked = ref(false);
const hasKveds = ref(false);
const userKvedList = ref([]);

const periodLabel = computed(() => {
  if (props.startDate && props.endDate) {
    return `${props.startDate} — ${props.endDate}`;
  }
  return `календарний ${new Date().getFullYear()} рік`;
});

function formatUah(n) {
  if (n == null || Number.isNaN(n)) return '—';
  return `${Math.round(n).toLocaleString('uk-UA')} грн`;
}

async function ensureKvedsSynced() {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return [];

  const local = getStoredKveds(user.id);
  let server = [];
  try {
    const res = await api.getMyKveds();
    server = res.data?.kveds || [];
  } catch (e) {
    console.warn('getMyKveds failed', e);
  }

  if (!server.length && local.length) {
    try {
      const syncRes = await api.syncMyKveds(toKvedSyncPayload(local));
      server = syncRes.data?.saved?.map((r) => ({
        code: r.code,
        name: r.name,
      })) || local;
      setStoredKveds(user.id, server);
    } catch (e) {
      console.warn('KVED sync before recommend failed', e);
      server = local;
    }
  } else if (server.length) {
    setStoredKveds(user.id, server);
  }

  userKvedList.value = server.length ? server : local;
  hasKveds.value = userKvedList.value.length > 0;
  kvedChecked.value = true;
  return userKvedList.value;
}

async function refreshKvedStatus() {
  await ensureKvedsSynced();
}

onMounted(() => {
  refreshKvedStatus();
});

async function fetchRecommendation() {
  loading.value = true;
  error.value = null;
  try {
    await ensureKvedsSynced();
    const params = { g4_land_type: 'arable_pasture' };
    if (props.startDate && props.endDate) {
      params.start_date = props.startDate;
      params.end_date = props.endDate;
    }
    if (b2bOverride.value !== null) {
      params.is_b2b_or_foreign = b2bOverride.value;
    }
    const res = await api.getFopGroupRecommend(params);
    result.value = res.data;
  } catch (e) {
    const msg = e.response?.data?.detail || 'Не вдалося розрахувати рекомендацію';
    error.value = typeof msg === 'string' ? msg : JSON.stringify(msg);
    notificationStore.showError(error.value);
  } finally {
    loading.value = false;
  }
}

const evaluation = computed(() => result.value?.evaluation);
const criteria = computed(() => evaluation.value?.criteria);
const groups = computed(() => evaluation.value?.groups || []);
const kvedValidation = computed(() => result.value?.kved_validation);
const generalSystem = computed(() => result.value?.general_system);
const overall = computed(() => result.value?.overall_recommendation);

const headlineResult = computed(() => {
  if (!overall.value) return null;
  if (overall.value.recommended_tax_system === 'general') {
    const vat = generalSystem.value?.with_vat;
    return {
      title: vat ? 'Загальна система з ПДВ' : 'Загальна система',
      group: null,
      tax: overall.value.recommended_annual_tax_uah,
    };
  }
  return {
    title: `Спрощена система — ${overall.value.recommended_fop_group} група`,
    group: overall.value.recommended_fop_group,
    tax: overall.value.recommended_annual_tax_uah,
  };
});
</script>

<template>
  <section class="bg-white rounded-[2rem] sm:rounded-[2.5rem] shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-10 space-y-8">
    <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
      <div class="flex items-start gap-4">
        <div class="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-100/50 shrink-0">
          <ClipboardList :size="28" stroke-width="2.5" />
        </div>
        <div>
          <h2 class="text-2xl font-black text-gray-900 tracking-tight">Рекомендація системи оподаткування</h2>
          <p class="text-sm text-gray-500 font-medium mt-1">
            Операції, КВЕД, найм, B2B/іноземні — період: {{ periodLabel }}
          </p>
        </div>
      </div>
      <button
        type="button"
        class="shrink-0 inline-flex items-center justify-center gap-2 px-8 py-4 rounded-2xl bg-indigo-600 text-white font-black text-sm hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all disabled:opacity-60"
        :disabled="loading"
        @click="fetchRecommendation"
      >
        <Loader2 v-if="loading" :size="18" class="animate-spin" />
        Дізнатися рекомендовану групу ФОП
      </button>
    </div>

    <div
      v-if="kvedChecked && hasKveds"
      class="p-4 rounded-2xl bg-emerald-50 border border-emerald-100 text-sm text-emerald-900"
    >
      <p class="font-black text-[10px] uppercase tracking-widest text-emerald-700 mb-2">Ваші КВЕД</p>
      <p class="font-medium">
        {{ userKvedList.map((k) => k.code).join(', ') }}
      </p>
    </div>

    <div
      v-else-if="kvedChecked && !hasKveds && !loading"
      class="p-4 rounded-2xl bg-amber-50 border border-amber-100 text-sm text-amber-900 flex gap-3"
    >
      <BookOpen class="shrink-0 mt-0.5" :size="18" />
      <p>
        Додайте КВЕД у
        <RouterLink to="/settings" class="font-black text-amber-800 underline">налаштуваннях</RouterLink>
        і натисніть «Зберегти» — без них перевірка заборонених кодів неможлива.
      </p>
    </div>

    <div class="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-3">
      <p class="text-xs font-black text-slate-500 uppercase tracking-widest">B2B / іноземні замовники</p>
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all"
          :class="b2bOverride === null ? 'bg-indigo-600 text-white' : 'bg-white text-gray-500 border border-gray-200'"
          @click="b2bOverride = null"
        >
          Авто
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all"
          :class="b2bOverride === true ? 'bg-amber-600 text-white' : 'bg-white text-gray-500 border border-gray-200'"
          @click="b2bOverride = true"
        >
          Так (IT / QA / ЗЕД)
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all"
          :class="b2bOverride === false ? 'bg-emerald-600 text-white' : 'bg-white text-gray-500 border border-gray-200'"
          @click="b2bOverride = false"
        >
          Ні
        </button>
      </div>
    </div>

    <p v-if="error" class="text-sm font-bold text-red-600 flex items-center gap-2">
      <AlertTriangle :size="16" />
      {{ error }}
    </p>

    <div v-if="result && headlineResult" class="space-y-8 animate-fade-in">
      <div
        class="p-6 sm:p-8 rounded-3xl border-2"
        :class="overall.recommended_tax_system === 'general' ? 'border-amber-200 bg-amber-50/50' : 'border-indigo-200 bg-indigo-50/50'"
      >
        <p class="text-[10px] font-black uppercase tracking-widest mb-2 text-gray-500">Підсумок</p>
        <p class="text-2xl sm:text-3xl font-black text-gray-900">{{ headlineResult.title }}</p>
        <p v-if="headlineResult.tax != null" class="text-sm font-bold text-gray-700 mt-2">
          Оціночне річне навантаження: {{ formatUah(headlineResult.tax) }}
        </p>
        <p class="text-sm text-gray-600 mt-2">{{ evaluation?.focusSummary?.headline }}</p>
      </div>

      <div
        v-if="kvedValidation?.blocks_simplified_system"
        class="p-5 rounded-2xl bg-red-50 border border-red-100 text-sm text-red-900"
      >
        <p class="font-black mb-2">КВЕД блокує спрощену систему</p>
        <ul class="list-disc pl-5 space-y-1">
          <li v-for="v in kvedValidation.simplified_violations" :key="v.user_code + v.pattern">
            {{ v.user_code }} — {{ v.title }}
          </li>
        </ul>
      </div>

      <div v-if="generalSystem" class="p-5 rounded-2xl border border-amber-100 bg-amber-50/30 space-y-3">
        <p class="text-xs font-black text-amber-800 uppercase tracking-widest">Загальна система</p>
        <p class="text-sm text-gray-700">
          {{ generalSystem.note }}
        </p>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div>
            <span class="text-gray-400 text-[10px] font-black uppercase block">ПДФО</span>
            <span class="font-bold">{{ formatUah(generalSystem.breakdown?.pit_uah) }}</span>
          </div>
          <div>
            <span class="text-gray-400 text-[10px] font-black uppercase block">ВЗ</span>
            <span class="font-bold">{{ formatUah(generalSystem.breakdown?.military_tax_uah) }}</span>
          </div>
          <div>
            <span class="text-gray-400 text-[10px] font-black uppercase block">ЄСВ</span>
            <span class="font-bold">{{ formatUah(generalSystem.breakdown?.esv_uah) }}</span>
          </div>
          <div v-if="generalSystem.with_vat">
            <span class="text-gray-400 text-[10px] font-black uppercase block">ПДВ (~20%)</span>
            <span class="font-bold text-amber-800">{{ formatUah(generalSystem.breakdown?.vat_estimate_uah) }}</span>
          </div>
        </div>
        <p v-if="generalSystem.with_vat" class="text-xs text-amber-800 font-medium">
          Оборот {{ formatUah(generalSystem.gross_income_uah) }} &gt;
          {{ formatUah(generalSystem.vat_threshold_uah) }} — модель з обов’язковим ПДВ.
        </p>
      </div>

      <div
        v-if="kvedValidation?.allow"
        class="p-4 rounded-2xl bg-slate-50 border border-slate-100 grid grid-cols-2 sm:grid-cols-5 gap-3 text-center"
      >
        <div>
          <p class="text-[9px] font-black text-gray-400 uppercase">1 гр.</p>
          <p class="font-black" :class="kvedValidation.allow.group_1 ? 'text-emerald-600' : 'text-red-600'">
            {{ kvedValidation.allow.group_1 ? 'Так' : 'Ні' }}
          </p>
        </div>
        <div>
          <p class="text-[9px] font-black text-gray-400 uppercase">2 гр.</p>
          <p class="font-black" :class="kvedValidation.allow.group_2 ? 'text-emerald-600' : 'text-red-600'">
            {{ kvedValidation.allow.group_2 ? 'Так' : 'Ні' }}
          </p>
        </div>
        <div>
          <p class="text-[9px] font-black text-gray-400 uppercase">3 гр.</p>
          <p class="font-black" :class="kvedValidation.allow.group_3 ? 'text-emerald-600' : 'text-red-600'">
            {{ kvedValidation.allow.group_3 ? 'Так' : 'Ні' }}
          </p>
        </div>
        <div>
          <p class="text-[9px] font-black text-gray-400 uppercase">4 гр.</p>
          <p class="font-black" :class="kvedValidation.allow.group_4 ? 'text-emerald-600' : 'text-red-600'">
            {{ kvedValidation.allow.group_4 ? 'Так' : 'Ні' }}
          </p>
        </div>
        <div>
          <p class="text-[9px] font-black text-gray-400 uppercase">Спрощ.</p>
          <p class="font-black" :class="kvedValidation.allow.simplified_system ? 'text-emerald-600' : 'text-red-600'">
            {{ kvedValidation.allow.simplified_system ? 'Так' : 'Ні' }}
          </p>
        </div>
      </div>

      <div v-if="criteria" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100">
          <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Дохід (прогноз)</p>
          <p class="text-lg font-black text-gray-900 mt-1">{{ formatUah(criteria.projected_annual_income_uah) }}</p>
        </div>
        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100">
          <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Наймані</p>
          <p class="text-lg font-black text-gray-900 mt-1">{{ criteria.employees_count }}</p>
        </div>
        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100">
          <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">B2B / іноземні</p>
          <p class="text-lg font-black mt-1" :class="criteria.is_b2b_or_foreign ? 'text-amber-700' : 'text-emerald-700'">
            {{ criteria.is_b2b_or_foreign ? 'Так' : 'Ні' }}
          </p>
        </div>
        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100">
          <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Ліміти L₁–L₃</p>
          <p class="text-[11px] font-bold text-gray-700 mt-1">
            1 {{ criteria.income_within_limits?.g1 ? '✓' : '✗' }}
            2 {{ criteria.income_within_limits?.g2 ? '✓' : '✗' }}
            3 {{ criteria.income_within_limits?.g3 ? '✓' : '✗' }}
          </p>
        </div>
      </div>

      <div class="overflow-x-auto rounded-2xl border border-gray-100">
        <table class="w-full text-left text-sm">
          <thead>
            <tr class="bg-gray-50 text-[10px] font-black uppercase tracking-widest text-gray-400">
              <th class="px-5 py-4">Група (спрощена)</th>
              <th class="px-5 py-4">Статус</th>
              <th class="px-5 py-4">Податки / рік</th>
              <th class="px-5 py-4">Причина</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
              v-for="row in groups"
              :key="row.group"
              :class="row.group === evaluation?.recommendedGroup ? 'bg-indigo-50/60' : ''"
            >
              <td class="px-5 py-4 font-black">{{ row.group }}</td>
              <td class="px-5 py-4">
                <span v-if="row.eligible" class="inline-flex items-center gap-1 text-emerald-700 font-bold text-xs">
                  <CheckCircle2 :size="14" /> Так
                </span>
                <span v-else class="inline-flex items-center gap-1 text-red-600 font-bold text-xs">
                  <XCircle :size="14" /> Ні
                </span>
              </td>
              <td class="px-5 py-4 font-bold tabular-nums">
                {{ row.estimatedAnnualTaxUah != null ? formatUah(row.estimatedAnnualTaxUah) : '—' }}
              </td>
              <td class="px-5 py-4 text-xs text-gray-500 max-w-md">{{ row.disqualifyReason || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <ul v-if="evaluation?.recommendationReasons?.length" class="space-y-2 text-sm text-gray-600">
        <li v-for="(r, i) in evaluation.recommendationReasons" :key="i" class="flex gap-2">
          <span class="text-indigo-400 shrink-0">•</span>
          <span>{{ r }}</span>
        </li>
      </ul>

      <p class="text-[11px] text-gray-400 italic border-t border-gray-100 pt-4">{{ result.disclaimer }}</p>
    </div>
  </section>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
