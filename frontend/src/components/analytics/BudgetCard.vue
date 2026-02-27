<script setup>
import { computed } from 'vue';
import { Pencil, Trash2, AlertCircle } from 'lucide-vue-next';

const props = defineProps({
  budget: { type: Object, required: true },
  categoryName: { type: String, default: 'Загальний бюджет' }
});

const emit = defineEmits(['edit', 'delete']);

const spentPercent = computed(() => {
  if (!props.budget.amount) return 0;
  return Math.min(100, Math.round((props.budget.spent / props.budget.amount) * 100));
});

const progressColor = computed(() => {
  if (spentPercent.value >= 100) return 'bg-red-600';
  if (spentPercent.value >= 90) return 'bg-red-500';
  if (spentPercent.value >= 75) return 'bg-yellow-400';
  return 'bg-green-500';
});
</script>

<template>
  <div class="bg-white p-6 rounded-[2rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col gap-4 relative group transition-all hover:shadow-2xl">
    <div class="flex justify-between items-start">
      <div>
        <h3 class="font-black text-gray-800 text-xl tracking-tight">{{ categoryName }}</h3>
        <p class="text-xs font-bold text-gray-400 mt-1 uppercase tracking-wider">
          {{ budget.period === 'monthly' ? 'Місячний' : budget.period === 'weekly' ? 'Тижневий' : 'Річний' }} ліміт
        </p>
      </div>
      <div class="flex gap-2">
        <button @click="emit('edit', budget)" class="text-gray-400 hover:text-blue-500 p-2 transition-colors rounded-full hover:bg-blue-50"><Pencil :size="18" stroke-width="2.5"/></button>
        <button @click="emit('delete', budget.id)" class="text-gray-400 hover:text-red-500 p-2 transition-colors rounded-full hover:bg-red-50"><Trash2 :size="18" stroke-width="2.5"/></button>
      </div>
    </div>

    <div class="mt-2">
      <div class="flex justify-between items-end mb-3">
        <div class="flex flex-col">
          <span class="text-2xl font-black text-gray-900">{{ Number(budget.spent).toLocaleString('uk-UA') }} ₴</span>
          <span class="text-sm font-semibold text-gray-400">витрачено</span>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-lg font-bold text-gray-600">з {{ Number(budget.amount).toLocaleString('uk-UA') }} ₴</span>
          <span class="text-sm font-bold" :class="spentPercent >= 90 ? 'text-red-500' : 'text-gray-400'">{{ spentPercent }}%</span>
        </div>
      </div>
      
      <div class="h-4 w-full bg-gray-100 rounded-full overflow-hidden shadow-inner flex">
        <div 
          class="h-full transition-all duration-700 ease-out rounded-full" 
          :class="progressColor" 
          :style="{ width: `${spentPercent}%` }"
        ></div>
      </div>
      
      <!-- Сповіщення про стан бюджету -->
      <div v-if="spentPercent >= 100" class="flex items-center gap-2 mt-4 text-white bg-red-600 px-4 py-3 rounded-xl border border-red-700 shadow-lg shadow-red-200">
        <AlertCircle :size="18" stroke-width="2.5" />
        <p class="text-xs font-bold uppercase tracking-wider text-white">Ліміт вичерпано!</p>
      </div>
      <div v-else-if="spentPercent >= 90" class="flex items-center gap-2 mt-4 text-red-500 bg-red-50 px-4 py-3 rounded-xl border border-red-100">
        <AlertCircle :size="18" stroke-width="2.5" />
        <p class="text-xs font-bold uppercase tracking-wider">Бюджет майже вичерпано!</p>
      </div>
    </div>
  </div>
</template>
