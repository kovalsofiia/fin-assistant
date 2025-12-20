<script setup>
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import { Calculator, Info } from 'lucide-vue-next';

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
    <h2 class="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
      <Calculator class="w-5 h-5 text-blue-600" />
      Податкове зобов'язання
    </h2>
    
    <!-- Total Block -->
    <div class="bg-blue-50 p-4 rounded-lg flex justify-between items-center mb-6 border border-blue-100">
      <span class="text-blue-800 font-medium text-sm uppercase tracking-wide">Всього до сплати</span>
      <SkeletonLoader v-if="loading" width="100px" height="28px" className="bg-blue-100" />
      <span v-else class="text-2xl font-bold text-blue-900">{{ (calculations.total || 0).toFixed(2) }} ₴</span>
    </div>

    <!-- Breakdown List -->
    <div class="space-y-3 flex-1">
      <div class="flex justify-between text-sm text-gray-600 border-b border-dashed border-gray-200 pb-2">
        <span class="flex items-center gap-2">
          <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
          Єдиний податок ({{ settings?.income_tax_percent }}%)
        </span>
        <SkeletonLoader v-if="loading" width="70px" height="18px" className="bg-gray-100" />
        <span v-else class="font-medium text-gray-800 font-mono">{{ (calculations.ep || 0).toFixed(2) }} ₴</span>
      </div>
      
      <div class="flex justify-between text-sm text-gray-600 border-b border-dashed border-gray-200 pb-2">
        <span class="flex items-center gap-2">
          <span class="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
          Військовий збір ({{ settings?.military_tax_percent }}%)
        </span>
        <SkeletonLoader v-if="loading" width="70px" height="18px" className="bg-gray-100" />
        <span v-else class="font-medium text-gray-800 font-mono">{{ (calculations.vz || 0).toFixed(2) }} ₴</span>
      </div>
      
      <div class="flex justify-between text-sm text-gray-600 pb-2">
        <span class="flex items-center gap-2">
          <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
          ЄСВ (фіксований)
        </span>
        <SkeletonLoader v-if="loading" width="70px" height="18px" className="bg-gray-100" />
        <span v-else class="font-medium text-gray-800 font-mono">{{ (calculations.esv || 0).toFixed(2) }} ₴</span>
      </div>
    </div>
    
    <!-- Note -->
    <div class="mt-6 pt-4 border-t border-gray-100 text-xs text-gray-400 italic flex items-start gap-1.5">
      <Info class="w-3.5 h-3.5 mt-0.5 shrink-0" />
      <span>Розрахунок є орієнтовним та базується на поточному доході та вказаних ставках.</span>
    </div>
  </div>
</template>