<script setup>
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import { Calculator, Info } from 'lucide-vue-next';
import { APP_CONSTANTS } from '@/constants/appConstants';

const tax = APP_CONSTANTS.TAX_2025;

defineProps({
  calculations: {
    type: Object,
    required: true // { total, ep, vz, esv }
  },
  settings: {
    type: Object,
    default: () => ({ income_tax_percent: 5, military_tax_percent: 1.5 })
  },
  loading: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-full flex flex-col">
    <div class="flex flex-col mb-4">
      <h2 class="text-xl font-black text-gray-900 flex items-center gap-3">
        <Calculator class="w-6 h-6 text-indigo-600" />
        Податковий розрахунок
      </h2>
      <p v-if="settings" class="text-[10px] font-black text-indigo-600 uppercase tracking-widest mt-1">
        ФОП {{ settings.fop_group }}-ї групи • 2025
      </p>
    </div>
    
    <!-- Total Block -->
    <div class="bg-blue-50 p-4 rounded-lg flex justify-between items-center mb-6 border border-blue-100">
      <span class="text-blue-800 font-medium text-sm uppercase tracking-wide">Всього до сплати</span>
      <SkeletonLoader v-if="loading" width="100px" height="28px" className="bg-blue-100" />
      <span v-else class="text-2xl font-bold text-blue-900">{{ (calculations.total || 0).toFixed(2) }} ₴</span>
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
          <span class="text-sm font-bold text-gray-700" v-if="settings?.fop_group === 3">Ставка {{ tax.GROUP_3_MILITARY_RATE * 100 }}%</span>
          <span class="text-sm font-bold text-gray-700" v-else>Фіксовано {{ tax.FIXED_MILITARY_TAX }} ₴</span>
        </div>
        <SkeletonLoader v-if="loading" width="70px" height="18px" />
        <span v-else class="font-black text-gray-900">{{ (calculations.vz || 0).toFixed(2) }} ₴</span>
      </div>
      
      <div class="flex justify-between items-center bg-gray-50/50 p-3 rounded-2xl border border-gray-100">
        <div class="flex flex-col">
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1">ЄСВ</span>
          <span class="text-sm font-bold text-gray-700">Ставка (мін. {{ tax.ESV_MONTHLY }})</span>
        </div>
        <SkeletonLoader v-if="loading" width="70px" height="18px" />
        <span v-else class="font-black text-gray-900">{{ (calculations.esv || 0).toFixed(2) }} ₴</span>
      </div>
    </div>
    
    <!-- Note -->
    <div class="mt-6 pt-4 border-t border-gray-100 text-xs text-gray-400 italic flex items-start gap-1.5">
      <Info class="w-3.5 h-3.5 mt-0.5 shrink-0" />
      <span>Розрахунок є орієнтовним та базується на поточному доході та вказаних ставках.</span>
    </div>
  </div>
</template>