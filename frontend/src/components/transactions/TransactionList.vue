<script setup>
import { 
  Calendar, FileText, ArrowUpRight, ArrowDownLeft 
} from 'lucide-vue-next';
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';

const props = defineProps({
  transactions: {
    type: Array,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  getCategoryName: {
    type: Function,
    required: true
  }
});

const emit = defineEmits(['open-details']);
</script>

<template>
  <div class="transaction-list-container">
    <!-- Mobile Transactions List (sm hidden) -->
    <div class="block sm:hidden space-y-4">
      <div v-if="isLoading" class="space-y-4">
        <div v-for="i in 5" :key="i" class="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm animate-pulse space-y-3">
          <div class="flex justify-between items-center">
            <SkeletonLoader width="100px" height="20px" />
            <SkeletonLoader width="80px" height="24px" borderRadius="10px" />
          </div>
          <div class="flex justify-between items-end">
            <div class="space-y-2">
              <SkeletonLoader width="120px" height="16px" />
              <SkeletonLoader width="60px" height="12px" />
            </div>
            <div class="flex gap-2">
              <SkeletonLoader width="36px" height="36px" borderRadius="10px" />
              <SkeletonLoader width="36px" height="36px" borderRadius="10px" />
            </div>
          </div>
        </div>
      </div>

      <template v-else>
        <div 
          v-for="tx in transactions" 
          :key="tx.transaction_id" 
          class="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm active:scale-[0.98] transition-all"
          @click="emit('open-details', tx)"
        >
          <div class="flex-grow space-y-4">
            <div class="flex justify-between items-start">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400">
                  <Calendar :size="18" />
                </div>
                <div class="flex flex-col">
                  <span class="text-xs font-black text-gray-400 uppercase tracking-widest">{{ new Date(tx.transaction_date).toLocaleDateString('uk-UA') }}</span>
                  <span class="font-bold text-gray-800">{{ getCategoryName(tx.category_id) }}</span>
                </div>
              </div>
              <div 
                class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider"
                :class="tx.transaction_type === 'income' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
              >
                {{ tx.transaction_type === 'income' ? 'Дохід' : 'Витрата' }}
              </div>
            </div>

            <div v-if="tx.notes" class="text-sm text-gray-500 font-medium italic bg-gray-50 p-3 rounded-xl">
              "{{ tx.notes }}"
            </div>

            <div class="flex justify-between items-end pt-2 border-t border-gray-50">
              <div class="flex flex-col">
                <div class="text-xl font-black tracking-tight" :class="tx.transaction_type === 'income' ? 'text-green-600' : 'text-red-600'">
                  {{ tx.transaction_type === 'income' ? '+' : '-' }}
                  {{ tx.transaction_amount.toLocaleString() }} ₴
                </div>
                <div v-if="tx.is_foreign_currency" class="text-[10px] font-black uppercase text-gray-400 mt-1 flex items-center gap-1">
                  {{ tx.amount_original }} {{ tx.currency_code }} <span class="text-gray-200">•</span> {{ tx.exchange_rate }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="transactions.length === 0" class="py-12 text-center bg-white rounded-3xl border-2 border-dashed border-gray-100">
           <FileText :size="40" class="mx-auto text-gray-200 mb-2" />
           <p class="font-black text-gray-300 uppercase tracking-widest text-xs">Записів не знайдено</p>
        </div>
      </template>
    </div>

    <!-- Table Section (Desktop only) -->
    <div class="hidden sm:block bg-white rounded-[2.5rem] shadow-2xl shadow-gray-200/50 border border-gray-50 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left">
          <thead>
            <tr class="bg-gray-50/50 border-b border-gray-50">
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Дата</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Категорія</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest">Коментар</th>
              <th class="px-8 py-6 text-xs font-black text-gray-400 uppercase tracking-widest text-right">Сума</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <!-- Skeleton Loading State -->
            <template v-if="isLoading">
              <tr v-for="i in 8" :key="i" class="animate-pulse">
                <td class="px-8 py-6">
                  <div class="flex items-center gap-3">
                    <SkeletonLoader width="40px" height="40px" borderRadius="12px" />
                    <SkeletonLoader width="100px" height="20px" />
                  </div>
                </td>
                <td class="px-8 py-6"><SkeletonLoader width="120px" height="24px" borderRadius="12px" /></td>
                <td class="px-8 py-6"><SkeletonLoader width="150px" height="20px" /></td>
                <td class="px-8 py-6">
                  <div class="flex flex-col items-end gap-1">
                    <SkeletonLoader width="100px" height="24px" />
                    <SkeletonLoader width="60px" height="12px" />
                  </div>
                </td>
              </tr>
            </template>

            <!-- Actual Data -->
            <template v-else>
              <tr 
                v-for="tx in transactions" 
                :key="tx.transaction_id" 
                class="group hover:bg-gray-50/50 transition-all cursor-pointer"
                @click="emit('open-details', tx)"
              >
                <td class="px-8 py-6">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 group-hover:bg-white group-hover:shadow-sm transition-all">
                      <Calendar :size="18" />
                    </div>
                    <span class="font-bold text-gray-700">{{ new Date(tx.transaction_date).toLocaleDateString('uk-UA') }}</span>
                  </div>
                </td>
                <td class="px-8 py-6">
                  <div 
                    class="inline-flex items-center px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-wider"
                    :class="tx.transaction_type === 'income' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                  >
                    {{ getCategoryName(tx.category_id) }}
                  </div>
                </td>
                <td class="px-8 py-6">
                  <span class="text-gray-500 font-medium italic">{{ tx.notes || '—' }}</span>
                </td>
                <td class="px-8 py-6 text-right">
                  <div class="flex flex-col items-end">
                    <div class="text-lg font-black tracking-tight" :class="tx.transaction_type === 'income' ? 'text-green-600' : 'text-red-600'">
                      {{ tx.transaction_type === 'income' ? '+' : '-' }}
                      {{ tx.transaction_amount.toLocaleString() }} ₴
                    </div>
                    <div v-if="tx.is_foreign_currency" class="text-[10px] font-black uppercase text-gray-400 mt-0.5 flex items-center gap-1">
                      {{ tx.amount_original }} {{ tx.currency_code }} <span class="text-gray-200">•</span> {{ tx.exchange_rate }}
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-if="transactions.length === 0">
                <td colspan="4" class="px-8 py-20 text-center">
                  <div class="flex flex-col items-center gap-4">
                    <div class="w-20 h-20 bg-gray-50 rounded-3xl flex items-center justify-center text-gray-200 mb-2">
                      <FileText :size="40" />
                    </div>
                    <p class="font-black text-gray-300 uppercase tracking-widest text-sm">
                      Записів не знайдено
                    </p>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
