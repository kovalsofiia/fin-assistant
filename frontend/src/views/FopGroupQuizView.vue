<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  ArrowLeft,
  ArrowRight,
  ClipboardList,
  Sparkles,
  AlertTriangle,
} from 'lucide-vue-next';
import {
  evaluateFopGroupQuiz,
  GROUP4_CONTEXT_NOTE,
  GROUP4_EP_FROM_NORMATIVE_NOTE,
  QUIZ_LEGAL_NOTE,
} from '@/utils/fopGroupQuizEngine';
import { useTaxRulesStore } from '@/stores/taxRulesStore';

const router = useRouter();
const taxRulesStore = useTaxRulesStore();

onMounted(() => {
  const now = new Date();
  taxRulesStore.fetchRules(now.getFullYear(), now.getMonth() + 1);
});

const quizCtx = computed(() => taxRulesStore.quizCtx);
const STEP_TITLES = {
  profile: 'Ваш профіль',
  flags: 'Особливості бізнесу',
  land: 'Сільгосп',
  result: 'На що звернути увагу',
};

const answers = reactive({
  projectedAnnualIncomeUah: 800_000,
  employeesBand: '0',
  activity: 'services',
  landAreaHa: 0,
  normativeLandValuePerHa: 0,
  /** Категорія землі для коефіцієнта ЄП 4 групи */
  g4LandType: 'arable_pasture',
  zedExport: false,
  expectsVatRegistration: false,
  /** Послуги/товари юрособам на загальній системі оподаткування */
  b2bLegalEntitiesGeneral: false,
  g1ActivityAllowed: true,
  esvCoveredElsewhere: false,
  fxIncomeSharePercent: 0,
});

/** 3–4 кроки: профіль → особливості → (сільгосп) → результат */
const stepIds = computed(() => {
  const s = ['profile', 'flags'];
  if (answers.activity === 'agriculture') s.push('land');
  s.push('result');
  return s;
});

const showG1Option = computed(
  () =>
    answers.employeesBand === '0' &&
    answers.activity !== 'agriculture' &&
    answers.projectedAnnualIncomeUah <= quizCtx.value.limits.g1
);

/** Один перемикач замість окремих кроків ЗЕД і «валюта %» */
const internationalOrZed = computed({
  get: () => answers.zedExport || answers.fxIncomeSharePercent > 0,
  set: (v) => {
    answers.zedExport = v;
    answers.fxIncomeSharePercent = v ? 100 : 0;
  },
});

watch(
  () => [answers.activity, answers.employeesBand],
  () => {
    if (answers.activity === 'trade' && answers.employeesBand === '0') {
      answers.g1ActivityAllowed = true;
    }
  }
);

const step = ref(0);

watch(stepIds, (ids) => {
  if (step.value >= ids.length) step.value = Math.max(0, ids.length - 1);
});

const currentStepId = computed(() => stepIds.value[step.value] ?? 'income');
const stepTitle = computed(() => STEP_TITLES[currentStepId.value] ?? '');
const totalStepsCount = computed(() => stepIds.value.length);
const progressPct = computed(() =>
  Math.round(((step.value + 1) / Math.max(1, totalStepsCount.value)) * 100)
);

const result = computed(() => evaluateFopGroupQuiz(answers, quizCtx.value));

const g4LandIncomplete = computed(() => {
  const ha = Number(answers.landAreaHa) || 0;
  const norm = Number(answers.normativeLandValuePerHa) || 0;
  return ha <= 0 || norm <= 0;
});

const g4LandPreview = computed(() => result.value.groups.find((g) => g.group === 4));

const isResultStep = computed(() => currentStepId.value === 'result');

function next() {
  if (step.value < totalStepsCount.value - 1) step.value += 1;
}

function back() {
  if (step.value > 0) step.value -= 1;
  else router.push('/settings');
}

const incomePresets = [
  { label: 'До ~1,4 млн', value: 1_000_000, hint: '1 група можлива' },
  { label: '~1,4–7 млн', value: 3_000_000, hint: '2 або 3 група' },
  { label: '~7–10 млн', value: 8_000_000, hint: '2 або 3 група' },
  { label: 'Понад ~10 млн', value: 10_500_000, hint: 'перевірка ліміту 3' },
];

function formatUah(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  return `${Math.round(n).toLocaleString('uk-UA')} грн`;
}
</script>

<template>
  <div class="max-w-2xl mx-auto p-4 sm:p-8 animate-fade-in font-sans pb-28">
    <header class="mb-8">
      <button
        type="button"
        class="flex items-center gap-2 text-gray-500 font-bold hover:text-gray-800 mb-6 transition-colors"
        @click="back"
      >
        <ArrowLeft :size="20" stroke-width="2.5" />
        Назад
      </button>
      <div class="flex items-start gap-4">
        <div class="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-lg shadow-indigo-200 shrink-0">
          <ClipboardList :size="28" stroke-width="2.5" />
        </div>
        <div>
          <h1 class="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight">Яка група ФОП вам ближча</h1>
          <p class="text-gray-500 font-medium mt-2">
            Короткий орієнтир {{ new Date().getFullYear() }} р. — на які групи звернути увагу, без податкової звітності.
          </p>
        </div>
      </div>

      <div class="mt-6 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          class="h-full bg-indigo-600 transition-all duration-300 rounded-full"
          :style="{ width: progressPct + '%' }"
        />
      </div>
      <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mt-2">
        Крок {{ step + 1 }} з {{ totalStepsCount }} · {{ stepTitle }}
      </p>
    </header>

    <!-- profile -->
    <section v-show="currentStepId === 'profile'" class="space-y-8">
      <div class="space-y-4">
        <label class="block text-sm font-black text-gray-400 uppercase tracking-widest">Очікуваний річний дохід</label>
        <div class="grid gap-2 sm:grid-cols-2">
          <button
            v-for="p in incomePresets"
            :key="p.label"
            type="button"
            class="px-4 py-4 rounded-2xl text-left border-2 transition-all"
            :class="
              answers.projectedAnnualIncomeUah === p.value
                ? 'border-indigo-600 bg-indigo-50'
                : 'border-gray-100 bg-white hover:border-gray-200'
            "
            @click="answers.projectedAnnualIncomeUah = p.value"
          >
            <span class="font-black text-gray-900 block">{{ p.label }}</span>
            <span class="text-xs text-gray-500 mt-1 block">{{ p.hint }}</span>
          </button>
        </div>
        <input
          v-model.number="answers.projectedAnnualIncomeUah"
          type="number"
          min="0"
          step="1000"
          class="w-full px-5 py-3 rounded-2xl border-2 border-gray-100 focus:border-indigo-500 font-bold text-gray-900 outline-none"
          placeholder="Точніша сума (грн)"
        >
      </div>

      <div class="space-y-3">
        <p class="text-sm font-black text-gray-400 uppercase tracking-widest">Наймані працівники</p>
        <div class="grid gap-2">
          <label
            v-for="opt in [
              { v: '0', t: 'Немає' },
              { v: '1-10', t: '1–10' },
              { v: '11+', t: 'Понад 10' },
            ]"
            :key="opt.v"
            class="flex items-center gap-3 p-4 rounded-2xl border-2 cursor-pointer transition-all"
            :class="answers.employeesBand === opt.v ? 'border-indigo-600 bg-indigo-50' : 'border-gray-100'"
          >
            <input v-model="answers.employeesBand" type="radio" :value="opt.v" class="w-5 h-5 text-indigo-600">
            <span class="font-black text-gray-900">{{ opt.t }}</span>
          </label>
        </div>
      </div>

      <div class="space-y-3">
        <p class="text-sm font-black text-gray-400 uppercase tracking-widest">Основна діяльність</p>
        <select
          v-model="answers.activity"
          class="w-full px-5 py-4 rounded-2xl border-2 border-gray-100 focus:border-indigo-500 font-bold text-gray-900 outline-none bg-white"
        >
          <option value="services">Послуги</option>
          <option value="trade">Торгівля / ринок</option>
          <option value="production">Виробництво</option>
          <option value="agriculture">Сільське господарство</option>
          <option value="other">Інше</option>
        </select>
      </div>
    </section>

    <!-- flags -->
    <section v-show="currentStepId === 'flags'" class="space-y-3">
      <p class="text-sm text-gray-600 leading-relaxed mb-2">
        Позначте лише те, що стосується вас — це звужує орієнтир до 3 групи або 1 групи.
      </p>
      <label class="flex items-start gap-4 p-5 rounded-2xl border-2 border-gray-100 cursor-pointer hover:bg-gray-50">
        <input v-model="internationalOrZed" type="checkbox" class="mt-1 rounded border-gray-300 text-indigo-600 w-5 h-5">
        <span>
          <span class="font-black text-gray-900 block">Є ЗЕД або дохід у валюті</span>
          <span class="text-sm text-gray-500">Типовий орієнтир — 3 група.</span>
        </span>
      </label>
      <label class="flex items-start gap-4 p-5 rounded-2xl border-2 border-gray-100 cursor-pointer hover:bg-gray-50">
        <input v-model="answers.expectsVatRegistration" type="checkbox" class="mt-1 rounded border-gray-300 text-indigo-600 w-5 h-5">
        <span>
          <span class="font-black text-gray-900 block">Планую бути платником ПДВ</span>
          <span class="text-sm text-gray-500">Орієнтир — 3 група (інша ставка ЄП).</span>
        </span>
      </label>
      <p
        v-if="result.vatRegistrationWarning && currentStepId === 'flags'"
        class="text-xs text-amber-800 font-medium px-4"
      >
        Дохід понад {{ quizCtx.vatThreshold.toLocaleString('uk-UA') }} грн — можлива обов’язкова реєстрація ПДВ, але 2
        група лишається можливою, доки не обрали ПДВ вище.
      </p>
      <label class="flex items-start gap-4 p-5 rounded-2xl border-2 border-gray-100 cursor-pointer hover:bg-gray-50">
        <input v-model="answers.b2bLegalEntitiesGeneral" type="checkbox" class="mt-1 rounded border-gray-300 text-indigo-600 w-5 h-5">
        <span>
          <span class="font-black text-gray-900 block">Регулярно працюватиму з юрособами на загальній системі</span>
          <span class="text-sm text-gray-500">1–2 групи зазвичай не підходять.</span>
        </span>
      </label>
      <label
        v-if="showG1Option"
        class="flex items-start gap-4 p-5 rounded-2xl border-2 border-slate-100 bg-slate-50/80 cursor-pointer"
      >
        <input v-model="answers.g1ActivityAllowed" type="checkbox" class="mt-1 rounded border-gray-300 text-indigo-600 w-5 h-5">
        <span class="font-bold text-gray-800 leading-snug text-sm">
          Діяльність під 1 групу (ринок, побутові послуги населенню)
        </span>
      </label>
    </section>

    <!-- land -->
    <section v-show="currentStepId === 'land'" class="space-y-4">
      <p class="text-sm font-black text-gray-400 uppercase tracking-widest">Сільгосп — чи є земля для 4 групи?</p>
      <p class="text-sm text-gray-600">{{ GROUP4_CONTEXT_NOTE }}</p>
      <div
        v-if="g4LandIncomplete"
        class="p-5 rounded-2xl bg-amber-50 border-2 border-amber-200 text-sm text-amber-950 leading-relaxed flex gap-3"
        role="alert"
      >
        <AlertTriangle class="shrink-0 mt-0.5 text-amber-600" :size="22" />
        <div>
          <p class="font-black text-amber-900">4 група зараз недоступна</p>
          <p class="mt-1">
            Без <strong>площі угідь (га)</strong> та <strong>нормативної грошової оцінки (грн/га)</strong> квіз не зможе
            включити 4 групу в порівняння. Рекомендація буде орієнтована на <strong>3 групу</strong>, доки не заповните обидва поля.
          </p>
          <p v-if="g4LandPreview?.disqualifyReason" class="mt-2 text-xs font-medium text-amber-800/90">
            {{ g4LandPreview.disqualifyReason }}
          </p>
        </div>
      </div>
      <div
        v-else
        class="p-4 rounded-2xl bg-emerald-100/80 border border-emerald-200 text-sm font-bold text-emerald-900"
      >
        Земельні дані заповнені — 4 група може бути допустимою (за умови без найму та сільгосп-діяльності).
      </div>
      <div class="p-5 rounded-2xl bg-emerald-50/90 border border-emerald-100 text-sm text-emerald-950 leading-relaxed space-y-3">
        <p>{{ GROUP4_CONTEXT_NOTE }}</p>
        <p class="text-xs text-emerald-900/90 border-t border-emerald-200 pt-3">{{ GROUP4_EP_FROM_NORMATIVE_NOTE }}</p>
      </div>
      <label class="block text-xs font-bold text-gray-500 uppercase tracking-wide">Категорія земель (коефіцієнт до нормативної оцінки)</label>
      <select
        v-model="answers.g4LandType"
        class="w-full px-5 py-4 rounded-2xl border-2 border-gray-100 focus:border-emerald-500 font-bold text-gray-900 outline-none bg-white"
      >
        <option value="arable_pasture">Рілля, сіножаті, пасовища — {{ quizCtx.g4Rates.arable_pasture }}%</option>
        <option value="water">Землі водного фонду — {{ quizCtx.g4Rates.water }}%</option>
        <option value="closed_soil">Закритий ґрунт (теплиці тощо) — {{ quizCtx.g4Rates.closed_soil }}%</option>
      </select>
      <label class="block text-xs font-bold text-gray-500 uppercase">Площа сільськогосподарських угідь (га)</label>
      <input
        v-model.number="answers.landAreaHa"
        type="number"
        min="0"
        step="0.01"
        class="w-full px-5 py-4 rounded-2xl border-2 border-gray-100 focus:border-indigo-500 font-bold outline-none"
      >
      <label class="block text-xs font-bold text-gray-500 uppercase">Нормативна грошова оцінка (грн/га)</label>
      <input
        v-model.number="answers.normativeLandValuePerHa"
        type="number"
        min="0"
        step="1000"
        class="w-full px-5 py-4 rounded-2xl border-2 border-gray-100 focus:border-indigo-500 font-bold outline-none"
      >
      <p class="text-xs text-gray-500 leading-relaxed border-t border-gray-100 pt-4">
        Можна пропустити поля — тоді орієнтир буде на 3 групу для сільгоспу без даних землі.
      </p>
    </section>

    <!-- result -->
    <section v-show="currentStepId === 'result'" class="space-y-6">
      <div
        v-if="result.focusSummary?.primaryGroup"
        class="p-8 rounded-[2rem] bg-gradient-to-br from-indigo-600 to-violet-700 text-white shadow-2xl shadow-indigo-300/40"
      >
        <div class="flex items-center gap-3 mb-4">
          <Sparkles :size="28" />
          <span class="font-black uppercase tracking-widest text-sm text-white/80">Орієнтир</span>
        </div>
        <p class="text-5xl font-black tabular-nums">{{ result.focusSummary.primaryGroup }} група</p>
        <p class="mt-4 text-white/95 font-medium text-lg leading-snug">
          {{ result.focusSummary.headline }}
        </p>
        <p v-if="result.recommendedTaxUah != null" class="mt-3 text-sm text-white/80">
          Оціночне навантаження (ЄП + ВЗ + ЄСВ ФОП): ≈ {{ formatUah(result.recommendedTaxUah) }}
        </p>
      </div>

      <div
        v-if="result.focusSummary?.groupsToConsider?.length > 1"
        class="p-6 rounded-2xl border border-indigo-100 bg-indigo-50/40"
      >
        <p class="text-xs font-black text-indigo-900 uppercase tracking-widest mb-4">
          Також варто порівняти ({{ result.focusSummary.eligibleCount }} допустимі)
        </p>
        <ul class="space-y-3">
          <li
            v-for="item in result.focusSummary.groupsToConsider"
            :key="item.group"
            class="p-4 rounded-xl bg-white border border-indigo-100/80"
            :class="item.isPrimary ? 'ring-2 ring-indigo-500' : ''"
          >
            <p class="font-black text-gray-900">
              {{ item.group }} група
              <span v-if="item.isPrimary" class="text-indigo-600 text-sm font-bold ml-2">— пріоритет</span>
            </p>
            <p class="text-sm text-gray-600 mt-1">{{ item.hint }}</p>
          </li>
        </ul>
      </div>

      <div v-else class="p-6 rounded-2xl bg-red-50 border border-red-100 flex gap-3 text-red-900">
        <AlertTriangle class="shrink-0" :size="22" />
        <div>
          <p class="font-black">Немає допустимої групи за поточними відповідями</p>
          <p class="text-sm mt-1 opacity-90">Перевірте дохід проти лімітів або умови для 4 групи / 1 групи.</p>
        </div>
      </div>

      <details class="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">
        <summary class="px-5 py-4 font-black text-gray-800 cursor-pointer hover:bg-gray-50">
          Детальне порівняння груп і податків
        </summary>
        <table class="w-full text-left text-sm border-t border-gray-100">
          <thead class="bg-gray-50 text-xs font-black uppercase tracking-wider text-gray-400">
            <tr>
              <th class="px-5 py-3">Група</th>
              <th class="px-5 py-3">Статус</th>
              <th class="px-5 py-3 text-right">Податки / рік</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="row in result.groups" :key="row.group">
              <td class="px-5 py-3 font-black">{{ row.group }}</td>
              <td class="px-5 py-3">
                <span v-if="row.eligible" class="text-emerald-600 font-bold">Можлива</span>
                <span v-else class="text-gray-500 text-xs">{{ row.disqualifyReason }}</span>
              </td>
              <td class="px-5 py-3 text-right font-bold tabular-nums">
                {{ row.eligible ? formatUah(row.estimatedAnnualTaxUah) : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </details>

      <ul
        v-if="result.recommendationReasons?.length"
        class="p-5 rounded-2xl bg-gray-50 border border-gray-100 text-sm text-gray-700 space-y-2 list-disc pl-5"
      >
        <li v-for="(r, i) in result.recommendationReasons" :key="i">{{ r }}</li>
      </ul>

      <p class="text-xs text-gray-500 leading-relaxed">{{ QUIZ_LEGAL_NOTE }}</p>

      <button
        type="button"
        class="w-full py-4 rounded-2xl bg-gray-900 text-white font-black hover:bg-gray-800 transition-all"
        @click="router.push('/settings')"
      >
        Перейти до налаштувань ФОП
      </button>
    </section>

    <footer v-if="!isResultStep" class="fixed bottom-0 left-0 right-0 p-4 bg-white/90 backdrop-blur-xl border-t border-gray-100">
      <div class="max-w-2xl mx-auto flex gap-3">
        <button
          type="button"
          class="flex-1 py-4 rounded-2xl border-2 border-gray-200 font-black text-gray-700 hover:bg-gray-50 transition-all flex items-center justify-center gap-2"
          @click="back"
        >
          <ArrowLeft :size="20" /> Назад
        </button>
        <button
          type="button"
          class="flex-[2] py-4 rounded-2xl bg-indigo-600 text-white font-black hover:bg-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-200"
          @click="next"
        >
          Далі <ArrowRight :size="20" />
        </button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
