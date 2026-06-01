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
  Sparkles,
  Loader2,
  AlertTriangle,
  ChevronDown,
  Settings2,
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
  return `${new Date().getFullYear()} рік`;
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

onMounted(() => {
  ensureKvedsSynced();
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
    const msg = e.response?.data?.detail || 'Не вдалося сформувати рекомендацію';
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
const snapshot = computed(() => result.value?.snapshot);

const recommendationLabel = computed(() => {
  if (!overall.value) return null;
  if (overall.value.recommended_tax_system === 'general') {
    return generalSystem.value?.with_vat
      ? 'Загальна система (з ПДВ)'
      : 'Загальна система';
  }
  return `Спрощена система, ${overall.value.recommended_fop_group} група`;
});

const recommendationTax = computed(() => overall.value?.recommended_annual_tax_uah);

const methodologyLine = computed(() => {
  if (!result.value) return '';
  const income = formatUah(snapshot.value?.projected_annual_income_uah);
  return `За операціями за ${periodLabel.value} (прогноз доходу ${income}) порівняно спрощену та загальну системи.`;
});

const simplifiedTransition = computed(() => result.value?.simplified_transition);

const keyAlerts = computed(() => {
  const items = [];
  const st = simplifiedTransition.value;
  if (st?.exceeded_absolute_limit) {
    items.push({
      type: 'warn',
      text:
        `Перевищено ліміт спрощеної (${formatUah(st.limit_uah)}): орієнтовно ${formatUah(st.excess_tax_15pct_uah)} за 15% з надлишку; `
        + 'з наступного кварталу — загальна система з обов’язковим ПДВ.',
    });
  }
  if (kvedValidation.value?.blocks_simplified_system) {
    const codes = (kvedValidation.value.simplified_violations || [])
      .slice(0, 2)
      .map((v) => v.user_code)
      .join(', ');
    items.push({
      type: 'warn',
      text: `КВЕД обмежує спрощену систему${codes ? ` (${codes})` : ''}.`,
    });
  } else if (kvedChecked.value && !hasKveds.value) {
    items.push({
      type: 'info',
      text: 'КВЕД не вказані — перевірка кодів не виконувалась.',
    });
  }
  if (criteria.value?.is_b2b_or_foreign) {
    items.push({ type: 'info', text: 'B2B / іноземні клієнти — групи 1–2 не розглядались.' });
  }
  return items;
});

const comparisonRows = computed(() => {
  const rows = [];
  const eligibleSimplified = groups.value.filter((g) => g.eligible && g.estimatedAnnualTaxUah != null);
  for (const g of eligibleSimplified) {
    rows.push({
      id: `g${g.group}`,
      label: `Спрощена, ${g.group} гр.`,
      tax: g.estimatedAnnualTaxUah,
      recommended:
        overall.value?.recommended_tax_system === 'simplified' &&
        overall.value?.recommended_fop_group === g.group,
    });
  }
  if (generalSystem.value?.estimated_annual_tax_uah != null) {
    rows.push({
      id: 'general',
      label: generalSystem.value.with_vat ? 'Загальна (з ПДВ)' : 'Загальна',
      tax: generalSystem.value.estimated_annual_tax_uah,
      recommended: overall.value?.recommended_tax_system === 'general',
    });
  }
  return rows.sort((a, b) => (a.tax ?? 0) - (b.tax ?? 0));
});
</script>

<template>
  <section class="bg-white rounded-[2rem] sm:rounded-[2.5rem] shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-8 space-y-6">
    <!-- Вступ -->
    <div class="space-y-3">
      <div class="flex items-start gap-3">
        <div class="w-11 h-11 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center shrink-0">
          <Sparkles :size="22" stroke-width="2.5" />
        </div>
        <div>
          <h2 class="text-xl sm:text-2xl font-black text-gray-900 tracking-tight">
            Рекомендація щодо оподаткування
          </h2>
          <p class="text-sm text-gray-600 mt-1.5 leading-relaxed max-w-2xl">
            Система аналізує ваші фінансові операції, оцінює податкове навантаження для різних
            систем оподаткування та формує рекомендацію щодо найбільш вигідного варіанту.
          </p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 text-xs text-gray-500">
        <span class="px-2.5 py-1 rounded-lg bg-gray-50 border border-gray-100 font-medium">
          Період: {{ periodLabel }}
        </span>
        <span
          v-if="kvedChecked && hasKveds"
          class="px-2.5 py-1 rounded-lg bg-gray-50 border border-gray-100 font-medium"
        >
          КВЕД: {{ userKvedList.map((k) => k.code).join(', ') }}
        </span>
        <RouterLink
          v-else-if="kvedChecked && !hasKveds"
          to="/settings"
          class="px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-100 text-amber-800 font-bold hover:bg-amber-100"
        >
          Додати КВЕД →
        </RouterLink>
      </div>
    </div>

    <!-- Налаштування розрахунку (компактно) -->
    <details class="group rounded-xl border border-gray-100 bg-gray-50/50">
      <summary class="flex items-center gap-2 px-4 py-3 cursor-pointer list-none text-sm font-bold text-gray-600">
        <Settings2 :size="16" class="text-gray-400" />
        Параметри розрахунку
        <ChevronDown :size="16" class="ml-auto text-gray-400 transition-transform group-open:rotate-180" />
      </summary>
      <div class="px-4 pb-4 pt-0">
        <p class="text-xs text-gray-500 mb-2">B2B / іноземні замовники (за замовчуванням — авто)</p>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-bold transition-all"
            :class="b2bOverride === null ? 'bg-indigo-600 text-white' : 'bg-white text-gray-500 border border-gray-200'"
            @click="b2bOverride = null"
          >
            Авто
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-bold transition-all"
            :class="b2bOverride === true ? 'bg-amber-600 text-white' : 'bg-white text-gray-500 border border-gray-200'"
            @click="b2bOverride = true"
          >
            Так
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-bold transition-all"
            :class="b2bOverride === false ? 'bg-emerald-600 text-white' : 'bg-white text-gray-500 border border-gray-200'"
            @click="b2bOverride = false"
          >
            Ні
          </button>
        </div>
      </div>
    </details>

    <button
      type="button"
      class="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-indigo-600 text-white font-black text-sm hover:bg-indigo-700 shadow-lg shadow-indigo-200/80 transition-all disabled:opacity-60"
      :disabled="loading"
      @click="fetchRecommendation"
    >
      <Loader2 v-if="loading" :size="18" class="animate-spin" />
      {{ loading ? 'Аналізуємо…' : 'Отримати рекомендацію' }}
    </button>

    <p v-if="error" class="text-sm font-bold text-red-600 flex items-center gap-2">
      <AlertTriangle :size="16" />
      {{ error }}
    </p>

    <!-- Результат -->
    <div v-if="result && recommendationLabel" class="space-y-4 animate-fade-in">
      <div
        class="p-5 sm:p-6 rounded-2xl border-2"
        :class="
          overall.recommended_tax_system === 'general'
            ? 'border-amber-200 bg-gradient-to-br from-amber-50/80 to-white'
            : 'border-indigo-200 bg-gradient-to-br from-indigo-50/80 to-white'
        "
      >
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1">
          Рекомендований варіант
        </p>
        <p class="text-2xl font-black text-gray-900">{{ recommendationLabel }}</p>
        <p v-if="recommendationTax != null" class="text-base font-bold text-gray-700 mt-2">
          Орієнтовне навантаження на рік: {{ formatUah(recommendationTax) }}
        </p>
        <p class="text-sm text-gray-500 mt-3">{{ methodologyLine }}</p>
      </div>

      <ul v-if="keyAlerts.length" class="space-y-2">
        <li
          v-for="(alert, i) in keyAlerts"
          :key="i"
          class="text-sm px-3 py-2 rounded-xl border"
          :class="
            alert.type === 'warn'
              ? 'bg-red-50 border-red-100 text-red-800'
              : 'bg-amber-50/80 border-amber-100 text-amber-900'
          "
        >
          {{ alert.text }}
        </li>
      </ul>

      <!-- Стисле порівняння -->
      <div v-if="comparisonRows.length" class="rounded-xl border border-gray-100 overflow-hidden">
        <p class="px-4 py-2.5 text-[10px] font-black uppercase tracking-widest text-gray-400 bg-gray-50">
          Порівняння навантаження
        </p>
        <ul class="divide-y divide-gray-50">
          <li
            v-for="row in comparisonRows"
            :key="row.id"
            class="flex items-center justify-between gap-4 px-4 py-3 text-sm"
            :class="row.recommended ? 'bg-indigo-50/50' : ''"
          >
            <span class="font-bold text-gray-800">
              {{ row.label }}
              <span
                v-if="row.recommended"
                class="ml-2 text-[10px] uppercase tracking-wider text-indigo-600"
              >
                рекомендовано
              </span>
            </span>
            <span class="font-black tabular-nums text-gray-900 shrink-0">{{ formatUah(row.tax) }}</span>
          </li>
        </ul>
      </div>

      <!-- Деталі за бажанням -->
      <details class="group rounded-xl border border-gray-100">
        <summary class="px-4 py-3 cursor-pointer list-none text-sm font-bold text-gray-600 flex items-center gap-2">
          <ChevronDown
            :size="16"
            class="text-gray-400 transition-transform group-open:rotate-180"
          />
          Детальний розбір (групи, ліміти, причини)
        </summary>
        <div class="px-4 pb-4 space-y-4 border-t border-gray-50">
          <div v-if="criteria" class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div class="p-3 rounded-lg bg-gray-50">
              <span class="text-gray-400 block mb-0.5">Дохід</span>
              <span class="font-bold">{{ formatUah(criteria.projected_annual_income_uah) }}</span>
            </div>
            <div class="p-3 rounded-lg bg-gray-50">
              <span class="text-gray-400 block mb-0.5">Наймані</span>
              <span class="font-bold">{{ criteria.employees_count }}</span>
            </div>
            <div class="p-3 rounded-lg bg-gray-50">
              <span class="text-gray-400 block mb-0.5">B2B</span>
              <span class="font-bold">{{ criteria.is_b2b_or_foreign ? 'Так' : 'Ні' }}</span>
            </div>
            <div class="p-3 rounded-lg bg-gray-50">
              <span class="text-gray-400 block mb-0.5">Ліміти 1–3</span>
              <span class="font-bold">
                {{ criteria.income_within_limits?.g1 ? '✓' : '✗' }}
                {{ criteria.income_within_limits?.g2 ? '✓' : '✗' }}
                {{ criteria.income_within_limits?.g3 ? '✓' : '✗' }}
              </span>
            </div>
          </div>

          <div class="overflow-x-auto rounded-lg border border-gray-100 text-sm">
            <table class="w-full text-left">
              <thead>
                <tr class="bg-gray-50 text-[10px] font-black uppercase text-gray-400">
                  <th class="px-3 py-2">Група</th>
                  <th class="px-3 py-2">Допустима</th>
                  <th class="px-3 py-2">Податки/рік</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr
                  v-for="row in groups"
                  :key="row.group"
                  :class="row.group === evaluation?.recommendedGroup ? 'bg-indigo-50/40' : ''"
                >
                  <td class="px-3 py-2 font-bold">{{ row.group }}</td>
                  <td class="px-3 py-2">{{ row.eligible ? 'Так' : 'Ні' }}</td>
                  <td class="px-3 py-2 font-bold tabular-nums">
                    {{ row.estimatedAnnualTaxUah != null ? formatUah(row.estimatedAnnualTaxUah) : '—' }}
                  </td>
                </tr>
              </tbody>
            </table>
            <p
              v-for="row in groups.filter((g) => !g.eligible && g.disqualifyReason)"
              :key="'r' + row.group"
              class="px-3 py-2 text-xs text-gray-500 border-t border-gray-50"
            >
              <span class="font-bold text-gray-700">{{ row.group }} група:</span>
              {{ row.disqualifyReason }}
            </p>
          </div>

          <ul v-if="evaluation?.recommendationReasons?.length" class="text-xs text-gray-500 space-y-1">
            <li v-for="(r, i) in evaluation.recommendationReasons" :key="i">• {{ r }}</li>
          </ul>
        </div>
      </details>

      <p class="text-[11px] text-gray-400 leading-relaxed">
        Орієнтовний розрахунок. Узгодьте рішення з бухгалтером або ДПС.
      </p>
    </div>
  </section>
</template>

<style scoped>
details summary::-webkit-details-marker {
  display: none;
}
.animate-fade-in {
  animation: fadeIn 0.35s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
