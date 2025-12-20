<script setup>
import { onMounted, computed, ref } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import api from '@/api';
import { supabase } from '@/supabase';
import { APP_CONSTANTS } from '@/constants/appConstants'; // Переконайтесь, що цей файл існує або видаліть імпорт

// Імпорти компонентів (тепер використовуємо Tailwind-стилізовані версії, якщо вони будуть)
// Для StatCard та TaxWidget ми можемо або створити нові, або адаптувати існуючі.
// Тут я припускаю, що ми використовуємо їх прямо в шаблоні або імпортуємо оновлені версії.
import StatCard from '@/components/dashboard/StatCard.vue';
import TaxWidget from '@/components/dashboard/TaxWidget.vue';
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import { ArrowDownLeft, ArrowUpRight, Calculator, Info } from 'lucide-vue-next';

const txStore = useTransactionStore();
const settings = ref(null);
const profile = ref(null);
const userId = ref(null);
const isPageLoading = ref(true);

// Фільтрація періоду
const currentDate = new Date();
const currentMonth = ref(currentDate.getMonth());
const currentYear = ref(currentDate.getFullYear());
const selectedPeriodType = ref('month'); // 'month' або 'custom'

// Ініціалізація періоду (поточний місяць)
const setInitialPeriod = () => {
  const { start, end } = txStore.getMonthRange(currentYear.value, currentMonth.value);
  txStore.filters.startDate = start;
  txStore.filters.endDate = end;
};

onMounted(async () => {
  isPageLoading.value = true;
  const { data: { user } } = await supabase.auth.getUser();
  if (user) {
    userId.value = user.id;
    
    setInitialPeriod();

    try {
      // Завантажуємо все паралельно для швидкості
      const [profileRes] = await Promise.all([
        api.getProfile(user.id),
        txStore.fetchInitialData()
      ]);
      
      profile.value = profileRes.data;

      // Якщо ФОП - тягнемо налаштування
      if (profile.value?.is_fop) {
        const settingsRes = await api.getFopSettings(user.id);
        settings.value = settingsRes.data;
      }
    } catch (e) {
      console.error("Dashboard load error:", e);
      if (!profile.value) profile.value = { is_fop: true };
      if (!settings.value) settings.value = { income_tax_percent: 5, military_tax_percent: 1.5, esv_value: 1760 };
    } finally {
      isPageLoading.value = false;
    }
  }
});

// Зміна місяця
const changeMonth = async (delta) => {
  isPageLoading.value = true;
  currentMonth.value += delta;
  if (currentMonth.value > 11) {
    currentMonth.value = 0;
    currentYear.value++;
  } else if (currentMonth.value < 0) {
    currentMonth.value = 11;
    currentYear.value--;
  }
  
  const { start, end } = txStore.getMonthRange(currentYear.value, currentMonth.value);
  txStore.filters.startDate = start;
  txStore.filters.endDate = end;
  
  await Promise.all([
    txStore.fetchTransactions(),
    txStore.fetchLifetimeSummary()
  ]);
  isPageLoading.value = false;
};

const monthName = computed(() => {
  return new Intl.DateTimeFormat('uk-UA', { month: 'long' }).format(new Date(currentYear.value, currentMonth.value));
});

// Обчислення податків на льоту
const taxCalculations = computed(() => {
  if (!profile.value?.is_fop || !settings.value) return { total: 0, ep: 0, esv: 0, vz: 0 };

  const income = txStore.summary.totalIncome;
  
  // 1. Єдиний податок (напр. 5%)
  const ep = income * (settings.value.income_tax_percent / 100);
  
  // 2. ВЗ
  const vz = income * (settings.value.military_tax_percent / 100);
  
  // 3. ЄСВ (фіксований)
  const esv = settings.value.esv_value; 

  return {
    ep: ep,
    vz: vz,
    esv: esv,
    total: ep + vz + esv
  };
});

// Реальний баланс за весь час (Після податків)
const realBalance = computed(() => {
  const grossBalance = txStore.lifetimeSummary.balance;
  if (!profile.value?.is_fop || !settings.value) return grossBalance;

  const totalIncome = txStore.lifetimeSummary.totalIncome;
  const ep = totalIncome * (settings.value.income_tax_percent / 100);
  const vz = totalIncome * (settings.value.military_tax_percent / 100);
  const esv = (txStore.lifetimeSummary.monthsCount || 1) * settings.value.esv_value;

  return grossBalance - (ep + vz + esv);
});

// Чистий дохід після податків
const realProfit = computed(() => {
  if (!profile.value?.is_fop) return txStore.summary.netProfit;
  return txStore.summary.netProfit - taxCalculations.value.total;
});

// Форматування валюти
const formatMoney = (val) => {
  return (val || 0).toFixed(2) + ' ₴';
};

// Отримання назви категорії (допоміжна функція)
const getCategoryName = (id) => {
  if (!txStore.categories.all) return '...';
  const cat = txStore.categories.all.find(c => c.id === id);
  return cat ? cat.name : 'Без категорії';
};
</script>

<template>
  <div class="max-w-6xl mx-auto p-8 animate-fade-in space-y-8">
    <!-- Header with Period Selector -->
    <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-2">
      <div>
        <h1 class="text-3xl font-black text-gray-900 tracking-tight">Фінансовий огляд</h1>
        <p class="text-gray-500 font-medium mt-1">Огляд вашої активності за обраний період</p>
      </div>

      <!-- Month Selector -->
      <div class="flex items-center bg-white border border-gray-100 rounded-2xl p-1.5 shadow-sm">
        <button 
          @click="changeMonth(-1)"
          class="p-2 hover:bg-gray-50 rounded-xl text-gray-400 hover:text-blue-600 transition-all"
        >
          <ArrowDownLeft class="w-5 h-5 rotate-45" />
        </button>
        <div class="px-4 py-1 text-center min-w-[140px]">
          <span class="block text-[10px] font-black uppercase text-gray-400 tracking-widest leading-none mb-1">Період</span>
          <span class="font-black text-gray-700 capitalize">{{ monthName }} {{ currentYear }}</span>
        </div>
        <button 
          @click="changeMonth(1)"
          class="p-2 hover:bg-gray-50 rounded-xl text-gray-400 hover:text-blue-600 transition-all"
        >
          <ArrowUpRight class="w-5 h-5 rotate-45" />
        </button>
      </div>
    </header>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard 
        title="Загальний Баланс"
        :amount="formatMoney(realBalance)"
        :subtext="profile?.is_fop ? 'Прибуток за весь час' : 'Всього за весь час'"
        variant="primary"
        :loading="isPageLoading"
      />

      <StatCard 
        title="Поступлення коштів"
        :amount="formatMoney(txStore.summary.totalIncome)"
        subtext="За вибраний місяць"
        variant="white"
        amountColor="blue"
        :loading="isPageLoading"
      />

      <StatCard 
        title="Витрати"
        :amount="formatMoney(txStore.summary.totalExpense)"
        subtext="За вибраний місяць"
        variant="white"
        amountColor="red"
        :loading="isPageLoading"
      />

      <StatCard 
        title="Прибуток"
        :amount="formatMoney(realProfit)"
        :subtext="profile?.is_fop ? 'Після податків' : 'За місяць'"
        variant="white"
        amountColor="default"
        :loading="isPageLoading"
      />
    </div>

    <!-- Main Content Row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Tax Widget Column (Only for FOP) -->
      <div v-if="profile?.is_fop" class="lg:col-span-1">
        <TaxWidget 
          :calculations="taxCalculations" 
          :settings="settings" 
          :loading="isPageLoading || !settings"
        />
      </div>

      <!-- Recent Transactions List Column -->
      <div class="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div class="p-4 border-b flex justify-between items-center bg-gray-50">
          <h2 class="font-bold text-gray-700">Останні операції</h2>
          <router-link to="/transactions" class="text-sm text-blue-600 font-medium hover:text-blue-800 transition-colors">
            Всі транзакції →
          </router-link>
        </div>
        
        <div v-if="isPageLoading" class="divide-y divide-gray-100">
          <div v-for="i in 5" :key="i" class="p-6 flex justify-between items-center">
            <div class="flex items-center gap-4">
              <SkeletonLoader width="40px" height="40px" borderRadius="12px" />
              <div class="space-y-2">
                <SkeletonLoader width="120px" height="16px" />
                <SkeletonLoader width="80px" height="12px" />
              </div>
            </div>
            <div class="space-y-2 flex flex-col items-end">
              <SkeletonLoader width="60px" height="20px" />
              <SkeletonLoader width="40px" height="12px" />
            </div>
          </div>
        </div>
        
        <ul v-else class="divide-y divide-gray-100">
          <li v-for="tx in txStore.transactions.slice(0, 5)" :key="tx.transaction_id" class="p-4 hover:bg-gray-50 transition-colors flex justify-between items-center">
            
            <div class="flex items-center gap-3">
              <!-- Icon based on type -->
              <div :class="['p-2 rounded-full shrink-0', tx.transaction_type === 'income' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600']">
                <component 
                  :is="tx.transaction_type === 'income' ? ArrowDownLeft : ArrowUpRight" 
                  class="w-5 h-5"
                />
              </div>
              
              <div>
                <span class="block font-medium text-gray-800">
                  {{ getCategoryName(tx.category_id) }}
                </span>
                <span class="text-xs text-gray-500">
                  {{ new Date(tx.transaction_date).toLocaleDateString() }}
                </span>
              </div>
            </div>

            <div class="text-right">
              <div :class="['font-bold', tx.transaction_type === 'income' ? 'text-green-600' : 'text-gray-900']">
                {{ tx.transaction_type === 'income' ? '+' : '-' }}
                {{ tx.transaction_amount.toFixed(2) }} ₴
              </div>
              <div v-if="tx.is_foreign_currency" class="text-xs text-gray-400 mt-0.5">
                ({{ tx.amount_original }} {{ tx.currency_code }})
              </div>
            </div>
          </li>
          
          <li v-if="txStore.transactions.length === 0" class="p-8 text-center text-gray-400 italic">
            Транзакцій поки немає
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Анімація появи */
.animate-fade-in { animation: fadeIn 0.5s ease-out; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* Лоадер */
.loader {
    border: 2px solid #f3f3f3;
    border-radius: 50%;
    border-top: 2px solid #3b82f6; /* blue-500 */
    width: 20px;
    height: 20px;
    animation: spin 1s linear infinite;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>