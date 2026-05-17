<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  ArrowLeft,
  ArrowRight,
  ClipboardList,
  HelpCircle,
  Sparkles,
  AlertTriangle,
} from 'lucide-vue-next';
import {
  evaluateFopGroupQuiz,
  LIMITS_ANNUAL_UAH_2026,
  GROUP1_INCOME_LIMIT_MIN_WAGE_UNITS_2026,
  GROUP2_INCOME_LIMIT_MIN_WAGE_UNITS_2026,
  GROUP2_CONTEXT_NOTE,
  GROUP2_EMPLOYER_PAYROLL_NOTE,
  GROUP3_INCOME_LIMIT_MIN_WAGE_UNITS_2026,
  GROUP3_CONTEXT_NOTE,
  GROUP3_FX_ZED_NOTE,
  GROUP3_ZERO_INCOME_NOTE,
  GROUP3_EP_PERCENT_NON_VAT,
  GROUP3_EP_PERCENT_VAT_PAYER,
  GROUP3_MILITARY_PERCENT_OF_INCOME,
  GROUP4_CONTEXT_NOTE,
  GROUP4_EP_FROM_NORMATIVE_NOTE,
  GROUP4_NORMATIVE_RATE_PCT,
  GROUP4_REPORTING_NOTE,
  GROUP4_MILITARY_FIXED_MONTHLY_UAH,
  GROUP4_MILITARY_FIXED_ANNUAL_UAH,
  MONTHLY_FIXED_UAH_2026,
  ESV_MONTHLY_UAH_2026,
  VAT_SUPPLY_THRESHOLD_UAH,
  QUIZ_LEGAL_NOTE,
} from '@/utils/fopGroupQuizEngine';

const router = useRouter();

const STEP_TITLES = {
  income: 'Проєктований дохід',
  employees: 'Наймані працівники',
  activity: 'Вид діяльності',
  zedvat: 'ЗЕД та ПДВ',
  g1: '1 група (умови)',
  esv: 'ЄСВ з ФОП',
  fx: 'Валютний дохід',
  land: 'Земля (4 група)',
  result: 'Результат',
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
  g1ActivityAllowed: true,
  esvCoveredElsewhere: false,
  fxIncomeSharePercent: 0,
});

/** Динамічна послідовність екранів квізу */
const stepIds = computed(() => {
  const s = ['income', 'employees', 'activity', 'zedvat'];
  if (answers.employeesBand === '0') s.push('g1');
  s.push('esv', 'fx');
  if (answers.activity === 'agriculture') s.push('land');
  s.push('result');
  return s;
});

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

const result = computed(() => evaluateFopGroupQuiz(answers));

const isResultStep = computed(() => currentStepId.value === 'result');

function next() {
  if (step.value < totalStepsCount.value - 1) step.value += 1;
}

function back() {
  if (step.value > 0) step.value -= 1;
  else router.push('/settings');
}

const incomePresets = [
  { label: 'До 1,4 млн', value: 1_200_000 },
  { label: '3–5 млн', value: 4_000_000 },
  { label: '7–9 млн', value: 8_000_000 },
  { label: '10+ млн', value: 10_500_000 },
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
          <h1 class="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight">Квіз: яка група ФОП ближча</h1>
          <p class="text-gray-500 font-medium mt-2">
            Орієнтир {{ new Date().getFullYear() }} р., спрощені формули та ліміти — для планування, не для звітності.
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

    <!-- income -->
    <section v-show="currentStepId === 'income'" class="space-y-6">
      <label class="block text-sm font-black text-gray-400 uppercase tracking-widest">Очікуваний річний дохід (грн)</label>
      <input
        v-model.number="answers.projectedAnnualIncomeUah"
        type="number"
        min="0"
        step="1000"
        class="w-full px-5 py-4 rounded-2xl border-2 border-gray-100 focus:border-indigo-500 font-black text-xl text-gray-900 outline-none transition-all"
      >
      <div class="flex flex-wrap gap-2">
        <button
          v-for="p in incomePresets"
          :key="p.label"
          type="button"
          class="px-4 py-2 rounded-xl bg-gray-50 font-bold text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 border border-transparent hover:border-indigo-100 transition-all"
          @click="answers.projectedAnnualIncomeUah = p.value"
        >
          {{ p.label }}
        </button>
      </div>
      <div class="p-4 rounded-2xl bg-amber-50 border border-amber-100 text-sm text-amber-900 leading-relaxed flex gap-3">
        <HelpCircle class="shrink-0 mt-0.5" :size="18" />
        <span>
          Ліміти 2026: 1 група — {{ GROUP1_INCOME_LIMIT_MIN_WAGE_UNITS_2026 }} МЗП (до {{ LIMITS_ANNUAL_UAH_2026.g1.toLocaleString('uk-UA') }} грн);
          2 група — {{ GROUP2_INCOME_LIMIT_MIN_WAGE_UNITS_2026 }} МЗП (до {{ LIMITS_ANNUAL_UAH_2026.g2.toLocaleString('uk-UA') }} грн);
          3 група — {{ GROUP3_INCOME_LIMIT_MIN_WAGE_UNITS_2026 }} МЗП (до {{ LIMITS_ANNUAL_UAH_2026.g3.toLocaleString('uk-UA') }} грн).
        </span>
      </div>
    </section>

    <!-- employees -->
    <section v-show="currentStepId === 'employees'" class="space-y-4">
      <p class="text-sm font-black text-gray-400 uppercase tracking-widest">Наймані працівники</p>
      <div class="grid gap-3">
        <label
          v-for="opt in [
            { v: '0', t: 'Немає (0)' },
            { v: '1-10', t: 'Від 1 до 10' },
            { v: '11+', t: 'Більше 10' },
          ]"
          :key="opt.v"
          class="flex items-center gap-4 p-5 rounded-2xl border-2 cursor-pointer transition-all"
          :class="answers.employeesBand === opt.v ? 'border-indigo-600 bg-indigo-50' : 'border-gray-100 bg-white hover:border-gray-200'"
        >
          <input v-model="answers.employeesBand" type="radio" :value="opt.v" class="w-5 h-5 text-indigo-600">
          <span class="font-black text-gray-900">{{ opt.t }}</span>
        </label>
      </div>
      <p class="text-xs text-gray-500 leading-relaxed">
        1 група — без найму; 2 група — до 10 осіб одночасно; 3 група — без ліміту «10 осіб» (інші вимоги ПКУ лишаються).
      </p>
      <div class="p-5 rounded-2xl bg-slate-50 border border-slate-100 text-sm text-slate-700 leading-relaxed space-y-3">
        <p>{{ GROUP2_CONTEXT_NOTE }}</p>
        <p class="text-xs text-slate-600 border-t border-slate-200 pt-3">{{ GROUP2_EMPLOYER_PAYROLL_NOTE }}</p>
      </div>
      <div class="p-5 rounded-2xl bg-indigo-50/80 border border-indigo-100 text-sm text-indigo-950 leading-relaxed space-y-2">
        <p class="font-black text-indigo-900 uppercase tracking-wider text-xs">3 група</p>
        <p>{{ GROUP3_CONTEXT_NOTE }}</p>
      </div>
    </section>

    <!-- activity -->
    <section v-show="currentStepId === 'activity'" class="space-y-4">
      <p class="text-sm font-black text-gray-400 uppercase tracking-widest">Основний вид діяльності</p>
      <p class="text-xs text-gray-500 leading-relaxed">
        Для <strong>2 групи</strong> — HoReCa, мале виробництво, роздріб (B2C); для <strong>3 групи</strong> — IT, консалтинг, юрособи, ЗЕД; для <strong>4 групи</strong> орієнтир — лише агросектор і земельні ділянки (доступ не від обсягу доходу в тій самій логіці, що 1–3 групи).
      </p>
      <select
        v-model="answers.activity"
        class="w-full px-5 py-4 rounded-2xl border-2 border-gray-100 focus:border-indigo-500 font-bold text-gray-900 outline-none bg-white"
      >
        <option value="services">Послуги</option>
        <option value="trade">Торгівля</option>
        <option value="production">Виробництво</option>
        <option value="agriculture">Сільське господарство (земля)</option>
        <option value="other">Інше</option>
      </select>
    </section>

    <!-- zedvat -->
    <section v-show="currentStepId === 'zedvat'" class="space-y-6">
      <div class="p-4 rounded-2xl bg-violet-50 border border-violet-100 text-xs text-violet-950 leading-relaxed">
        {{ GROUP3_FX_ZED_NOTE }}
      </div>
      <label class="flex items-start gap-4 p-5 rounded-2xl border-2 border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors">
        <input v-model="answers.zedExport" type="checkbox" class="mt-1 rounded border-gray-300 text-indigo-600 w-5 h-5">
        <span>
          <span class="font-black text-gray-900 block">Є експорт / імпорт (ЗЕД)</span>
          <span class="text-sm text-gray-500">Може впливати на ПДВ і звітність окремо від спрощених ставок.</span>
        </span>
      </label>
      <label class="flex items-start gap-4 p-5 rounded-2xl border-2 border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors">
        <input v-model="answers.expectsVatRegistration" type="checkbox" class="mt-1 rounded border-gray-300 text-indigo-600 w-5 h-5">
        <span>
          <span class="font-black text-gray-900 block">Очікую реєстрацію платником ПДВ або постачання понад поріг (~{{ VAT_SUPPLY_THRESHOLD_UAH.toLocaleString('uk-UA') }} грн за 12 міс)</span>
          <span class="text-sm text-gray-500">
            Для 3 групи в квізі: неплатник ПДВ — ЄП {{ GROUP3_EP_PERCENT_NON_VAT }}% від доходу; платник ПДВ — ЄП {{ GROUP3_EP_PERCENT_VAT_PAYER }}% від доходу за квартал + ПДВ окремо в обліку.
          </span>
        </span>
      </label>
      <p class="text-xs text-gray-500 leading-relaxed px-1">{{ GROUP3_ZERO_INCOME_NOTE }}</p>
    </section>

    <!-- g1 -->
    <section v-show="currentStepId === 'g1'" class="space-y-4">
      <p class="text-sm font-black text-gray-400 uppercase tracking-widest">Чи підходить діяльність під 1 групу?</p>
      <div class="p-5 rounded-2xl bg-slate-50 border border-slate-100 text-sm text-slate-700 leading-relaxed space-y-3">
        <p>
          <strong>1 група</strong> — базовий рівень спрощеної системи для <strong>індивідуальної</strong> зайнятості: типово
          роздрібний продаж із торговельних місць на ринках або побутові послуги населенню (наприклад ремонт взуття, пошив одягу за переліком ПКУ).
        </p>
        <p>
          Наймані працівники для цієї групи <strong>не допускаються</strong>. Максимальний річний дохід 2026:
          <strong>{{ GROUP1_INCOME_LIMIT_MIN_WAGE_UNITS_2026 }} МЗП</strong> (до {{ LIMITS_ANNUAL_UAH_2026.g1.toLocaleString('uk-UA') }} грн).
        </p>
        <p class="text-xs text-slate-500 border-t border-slate-200 pt-3">
          Податки (орієнтир): ЄП фіксовано {{ MONTHLY_FIXED_UAH_2026.g1.single }} грн/міс; військовий збір
          {{ MONTHLY_FIXED_UAH_2026.g1.military }} грн/міс; ЄСВ {{ ESV_MONTHLY_UAH_2026 }} грн/міс (22% від МЗП).
        </p>
      </div>
      <label class="flex items-start gap-4 p-5 rounded-2xl border-2 border-gray-100 cursor-pointer hover:border-indigo-100 transition-colors">
        <input v-model="answers.g1ActivityAllowed" type="checkbox" class="mt-1 rounded border-gray-300 text-indigo-600 w-5 h-5">
        <span class="font-bold text-gray-800 leading-snug">
          Так, моя діяльність відповідає обмеженням для 1 групи та КВЕД (узгодити з бухгалтером за актуальним переліком)
        </span>
      </label>
    </section>

    <!-- esv -->
    <section v-show="currentStepId === 'esv'" class="space-y-4">
      <label class="flex items-start gap-4 p-5 rounded-2xl border-2 border-indigo-100 bg-indigo-50/50 cursor-pointer">
        <input v-model="answers.esvCoveredElsewhere" type="checkbox" class="mt-1 rounded border-gray-300 text-indigo-600 w-5 h-5">
        <span>
          <span class="font-black text-gray-900 block">Не нараховувати мінімальний ЄСВ з ФОП у порівнянні для 3 групи</span>
          <span class="text-sm text-gray-600">Якщо внесок уже покривається основним місцем — зменшуємо оцінку лише для 3 групи.</span>
        </span>
      </label>
      <p class="text-xs text-gray-400">
        Для 1–2 та 4 груп у квізі ЄСВ усе одно врахований типово ({{ ESV_MONTHLY_UAH_2026 }} грн/міс).
      </p>
    </section>

    <!-- fx -->
    <section v-show="currentStepId === 'fx'" class="space-y-4">
      <label class="block text-sm font-black text-gray-400 uppercase tracking-widest">Частка доходу в іноземній валюті (%)</label>
      <input
        v-model.number="answers.fxIncomeSharePercent"
        type="range"
        min="0"
        max="100"
        step="5"
        class="w-full accent-indigo-600"
      >
      <p class="text-center font-black text-2xl text-indigo-600">{{ answers.fxIncomeSharePercent }}%</p>
      <p class="text-xs text-gray-500 leading-relaxed">
        Для ліміту спрощеної системи дохід перераховується в гривні за курсом НБУ. Поле нагадує про валютну частку; порівняння груп за сумою в гривнях.
      </p>
    </section>

    <!-- land -->
    <section v-show="currentStepId === 'land'" class="space-y-4">
      <p class="text-sm font-black text-gray-400 uppercase tracking-widest">4 група — земельні дані</p>
      <div class="p-5 rounded-2xl bg-emerald-50/90 border border-emerald-100 text-sm text-emerald-950 leading-relaxed space-y-3">
        <p>{{ GROUP4_CONTEXT_NOTE }}</p>
        <p class="text-xs text-emerald-900/90 border-t border-emerald-200 pt-3">{{ GROUP4_EP_FROM_NORMATIVE_NOTE }}</p>
      </div>
      <label class="block text-xs font-bold text-gray-500 uppercase tracking-wide">Категорія земель (коефіцієнт до нормативної оцінки)</label>
      <select
        v-model="answers.g4LandType"
        class="w-full px-5 py-4 rounded-2xl border-2 border-gray-100 focus:border-emerald-500 font-bold text-gray-900 outline-none bg-white"
      >
        <option value="arable_pasture">Рілля, сіножаті, пасовища — {{ GROUP4_NORMATIVE_RATE_PCT.arable_pasture }}%</option>
        <option value="water">Землі водного фонду — {{ GROUP4_NORMATIVE_RATE_PCT.water }}%</option>
        <option value="closed_soil">Закритий ґрунт (теплиці тощо) — {{ GROUP4_NORMATIVE_RATE_PCT.closed_soil }}%</option>
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
        <strong>Військовий збір (орієнтир):</strong> фіксовано {{ GROUP4_MILITARY_FIXED_MONTHLY_UAH }} грн/міс (10% від МЗП), річний еквівалент
        {{ GROUP4_MILITARY_FIXED_ANNUAL_UAH.toLocaleString('uk-UA') }} грн. <strong>ЄСВ ФОП:</strong> {{ ESV_MONTHLY_UAH_2026 }} грн/міс на загальних підставах.
      </p>
      <p class="text-xs text-gray-500">{{ GROUP4_REPORTING_NOTE }}</p>
    </section>

    <!-- result -->
    <section v-show="currentStepId === 'result'" class="space-y-6">
      <div
        v-if="result.recommendedGroup"
        class="p-8 rounded-[2rem] bg-gradient-to-br from-indigo-600 to-violet-700 text-white shadow-2xl shadow-indigo-300/40"
      >
        <div class="flex items-center gap-3 mb-4">
          <Sparkles :size="28" />
          <span class="font-black uppercase tracking-widest text-sm text-white/80">Найменше оціночне навантаження серед допустимих</span>
        </div>
        <p class="text-5xl font-black tabular-nums">{{ result.recommendedGroup }} група</p>
        <p class="mt-4 text-white/90 font-medium">
          Оціночні податки на рік (ЄП + ВЗ + ЄСВ за моделлю квізу): ≈ {{ formatUah(result.recommendedTaxUah) }}
        </p>
      </div>

      <div v-else class="p-6 rounded-2xl bg-red-50 border border-red-100 flex gap-3 text-red-900">
        <AlertTriangle class="shrink-0" :size="22" />
        <div>
          <p class="font-black">Немає допустимої групи за поточними відповідями</p>
          <p class="text-sm mt-1 opacity-90">Перевірте дохід проти лімітів або умови для 4 групи / 1 групи.</p>
        </div>
      </div>

      <div class="rounded-[2rem] border border-gray-100 bg-white shadow-lg overflow-hidden">
        <table class="w-full text-left text-sm">
          <thead class="bg-gray-50 text-xs font-black uppercase tracking-wider text-gray-400">
            <tr>
              <th class="px-5 py-4">Група</th>
              <th class="px-5 py-4">Статус</th>
              <th class="px-5 py-4 text-right">Податки / рік (оцінка)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="row in result.groups" :key="row.group" class="hover:bg-gray-50/80">
              <td class="px-5 py-4 font-black text-gray-900">{{ row.group }}</td>
              <td class="px-5 py-4">
                <span v-if="row.eligible" class="text-emerald-600 font-bold">Допустима</span>
                <span v-else class="text-gray-500 text-xs leading-snug">{{ row.disqualifyReason }}</span>
              </td>
              <td class="px-5 py-4 text-right font-bold tabular-nums">
                {{ row.eligible ? formatUah(row.estimatedAnnualTaxUah) : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="p-5 rounded-2xl bg-gray-50 border border-gray-100 text-xs text-gray-600 leading-relaxed space-y-2">
        <p>
          <strong>1 група (орієнтир 2026):</strong> ЄП {{ MONTHLY_FIXED_UAH_2026.g1.single }} грн/міс (фіксована ставка незалежно від доходу в межах ліміту),
          ВЗ {{ MONTHLY_FIXED_UAH_2026.g1.military }} грн/міс; разом із ЄСВ модель квізу рахує річну суму ЄП+ВЗ+ЄСВ.
        </p>
        <p>
          <strong>2 група (орієнтир 2026):</strong> ліміт доходу {{ GROUP2_INCOME_LIMIT_MIN_WAGE_UNITS_2026 }} МЗП (до
          {{ LIMITS_ANNUAL_UAH_2026.g2.toLocaleString('uk-UA') }} грн). ЄП фіксовано {{ MONTHLY_FIXED_UAH_2026.g2.single }} грн/міс (20% від
          прожиткового мінімуму за правилами ПКУ), незалежно від доходу в межах ліміту; ВЗ {{ MONTHLY_FIXED_UAH_2026.g2.military }} грн/міс (10%
          від МЗП). ЄСВ самого ФОП — {{ ESV_MONTHLY_UAH_2026 }} грн/міс (22% від МЗП). Для найманих: утримання ПДФО 18%, ВЗ 5% із зарплати та нарахування ЄСВ 22% на фонд оплати праці (не входить у число в таблиці «податки ФОП» вище).
        </p>
        <p class="text-xs text-gray-500"><strong>Модель квізу</strong> порівнює лише фіксовані платежі самого ФОП + типовий ЄСВ ФОП; зарплатні утримання не додаються до суми в таблиці вище.</p>
        <p>
          <strong>3 група (орієнтир 2026):</strong> ліміт {{ GROUP3_INCOME_LIMIT_MIN_WAGE_UNITS_2026 }} МЗП (до {{ LIMITS_ANNUAL_UAH_2026.g3.toLocaleString('uk-UA') }} грн).
          ЄП — {{ GROUP3_EP_PERCENT_NON_VAT }}% від доходу (неплатник ПДВ) або {{ GROUP3_EP_PERCENT_VAT_PAYER }}% від доходу за квартал + ПДВ (платник ПДВ); військовий збір {{ GROUP3_MILITARY_PERCENT_OF_INCOME }}% від доходу (у квізі — від річного проєкту).
          ЄСВ ФОП — {{ ESV_MONTHLY_UAH_2026 }} грн/міс (22% від МЗП).
        </p>
        <p class="text-xs text-gray-500"><strong>Без доходу:</strong> {{ GROUP3_ZERO_INCOME_NOTE }}</p>
        <p>
          <strong>4 група (орієнтир 2026):</strong> лише сільгосп; доступ прив’язаний до земельних ділянок (угідь, водний фонд), ЄП від нормативної грошової оцінки × площа × ставку (обраний тип:
          {{ GROUP4_NORMATIVE_RATE_PCT[answers.g4LandType] ?? GROUP4_NORMATIVE_RATE_PCT.arable_pasture }}%). ВЗ фіксовано {{ GROUP4_MILITARY_FIXED_MONTHLY_UAH }} грн/міс (річний еквівалент {{ GROUP4_MILITARY_FIXED_ANNUAL_UAH.toLocaleString('uk-UA') }} грн); ЄСВ — {{ ESV_MONTHLY_UAH_2026 }} грн/міс. {{ GROUP4_REPORTING_NOTE }}
        </p>
        <p v-if="result.fxNote">{{ result.fxNote }}</p>
        <p v-if="result.zedNote">{{ result.zedNote }}</p>
        <p class="text-gray-500 pt-2 border-t border-gray-200">{{ QUIZ_LEGAL_NOTE }}</p>
      </div>

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
