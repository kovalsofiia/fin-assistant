<script setup>
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import { Calculator, Info } from 'lucide-vue-next';
import { useTaxRulesStore } from '@/stores/taxRulesStore';
import { computed } from 'vue';

import { APP_CONSTANTS } from '@/constants/appConstants';

const taxRulesStore = useTaxRulesStore();
const rules = computed(() => taxRulesStore.currentRules || {
  esv_value: APP_CONSTANTS.TAX_DEFAULTS.ESV_VALUE,
  single_tax_g1: APP_CONSTANTS.TAX_DEFAULTS.SINGLE_TAX_G1,
  single_tax_g2: APP_CONSTANTS.TAX_DEFAULTS.SINGLE_TAX_G2,
  fixed_military_tax: APP_CONSTANTS.TAX_DEFAULTS.FIXED_MILITARY_TAX,
  military_tax_percent: APP_CONSTANTS.TAX_DEFAULTS.MILITARY_TAX_PERCENT,
  income_tax_percent: APP_CONSTANTS.TAX_DEFAULTS.INCOME_TAX_G3
});

const props = defineProps({
  calculations: {
    type: Object,
    required: true // { total, ep, vz, esv }
  },
  settings: {
    type: Object,
    default: () => ({ 
      income_tax_percent: APP_CONSTANTS.TAX_DEFAULTS.INCOME_TAX_G3, 
      military_tax_percent: APP_CONSTANTS.TAX_DEFAULTS.MILITARY_TAX_PERCENT 
    })
  },
  loading: {
    type: Boolean,
    default: false
  },
  periodLabel: {
    type: String,
    default: 'обраний період'
  },
  paymentTermHint: {
    type: String,
    default: ''
  }
});

const isGroup3 = computed(() => props.settings?.fop_group === 3);
</script>

<template>
  <div class="bg-white rounded-[2rem] sm:rounded-[2.5rem] shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-8 h-full flex flex-col">
    <div class="flex flex-col mb-4">
      <h2 class="text-xl font-black text-gray-900 flex items-center gap-3">
        <Calculator class="w-6 h-6 text-indigo-600" />
        Податковий розрахунок
      </h2>
      <p v-if="settings" class="text-[10px] font-black text-indigo-600 uppercase tracking-widest mt-1">
        ФОП {{ settings.fop_group }}-ї групи • {{ rules.year || '2025' }}
      </p>
    </div>
    
    <!-- Total Block -->
    <div class="bg-blue-50 p-4 rounded-lg mb-6 border border-blue-100">
      <div class="flex justify-between items-center gap-3">
        <span class="text-blue-800 font-medium text-sm uppercase tracking-wide">
          Нараховано за {{ periodLabel }}
        </span>
        <SkeletonLoader v-if="loading" width="100px" height="28px" className="bg-blue-100" />
        <span v-else class="text-2xl font-bold text-blue-900">{{ (calculations.total || 0).toFixed(2) }} ₴</span>
      </div>
      <p v-if="isGroup3" class="text-xs text-blue-800/80 mt-2">
        Це оціночне нарахування за доходами періоду, не підтвердження фактичного платежу до ДПС.
      </p>
      <p v-if="isGroup3 && paymentTermHint" class="text-xs text-indigo-700 mt-1 font-semibold">
        Строк сплати (ФОП 3): {{ paymentTermHint }}
      </p>
    </div>

    <!-- Breakdown List -->
    <div class="space-y-4 flex-1">
      <div class="flex justify-between items-center bg-gray-50/50 p-3 rounded-2xl border border-gray-100">
        <div class="flex flex-col">
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1">Єдиний податок</span>
          <span class="text-sm font-bold text-gray-700" v-if="settings?.fop_group === 3">Ставка {{ settings?.income_tax_percent }}%</span>
          <span class="text-sm font-bold text-gray-700" v-else>Фіксована ставка</span>
        </div>
        <SkeletonLoader v-if="loading" width="70px" height="18px" />
        <span v-else class="font-black text-gray-900">{{ (calculations.ep || 0).toFixed(2) }} ₴</span>
      </div>
      
      <div class="flex justify-between items-center bg-gray-50/50 p-3 rounded-2xl border border-gray-100">
        <div class="flex flex-col">
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1">Військовий збір</span>
          <span class="text-sm font-bold text-gray-700" v-if="settings?.fop_group === 3">Ставка {{ rules.military_tax_percent || 1.0 }}%</span>
          <span class="text-sm font-bold text-gray-700" v-else>Фіксовано {{ rules.fixed_military_tax || 800 }} ₴</span>
        </div>
        <SkeletonLoader v-if="loading" width="70px" height="18px" />
        <span v-else class="font-black text-gray-900">{{ (calculations.vz || 0).toFixed(2) }} ₴</span>
      </div>
      
      <div class="flex justify-between items-center bg-gray-50/50 p-3 rounded-2xl border border-gray-100">
        <div class="flex flex-col">
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1">ЄСВ</span>
          <span class="text-sm font-bold text-gray-700">Ставка (мін. {{ (rules.esv_value || APP_CONSTANTS.TAX_DEFAULTS.ESV_VALUE).toFixed(2) }})</span>
        </div>
        <SkeletonLoader v-if="loading" width="70px" height="18px" />
        <span v-else class="font-black text-gray-900">{{ (calculations.esv || 0).toFixed(2) }} ₴</span>
      </div>
    </div>
    
    <!-- Note -->
    <div class="mt-6 pt-4 border-t border-gray-100 text-xs text-gray-400 italic flex items-start gap-1.5">
      <Info class="w-3.5 h-3.5 mt-0.5 shrink-0" />
      <span>Розрахунок є орієнтовним: нарахування рахується за періодом, а фактична сплата виконується за календарем ДПС.</span>
    </div>
  </div>
</template>