<script setup>
import { onMounted, computed, ref, watch } from 'vue';
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
import { ArrowDownLeft, ArrowUpRight, Calculator, Info, Clock } from 'lucide-vue-next';

const txStore = useTransactionStore();
const settings = ref(null);
const profile = ref(null);
const userId = ref(null);
const isPageLoading = ref(true);
const taxData = ref(null);
const taxWarnings = ref([]);
const paymentCalendar = ref([]);

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
    
    try {
      setInitialPeriod();

      // Завантажуємо все паралельно для швидкості
      const [profileRes] = await Promise.all([
        api.getProfile(user.id),
        txStore.fetchInitialData()
      ]);
      
      profile.value = profileRes.data;

      // Якщо ФОП - тягнемо налаштування та розрахунок податків
      if (profile.value?.is_fop) {
        const settingsRes = await api.getFopSettings(user.id);
        settings.value = settingsRes.data;
        await fetchTaxAnalysis();
      }
    } catch (e) {
      console.error("Dashboard load error:", e);
      if (!profile.value) profile.value = { is_fop: true };
    } finally {
      isPageLoading.value = false;
    }
  }
});

const fetchTaxAnalysis = async () => {
  if (!userId.value) return;
  try {
    const res = await api.get(`/tax/calculate`, {
      params: {
        user_id: userId.value,
        annual_income: txStore.lifetimeSummary.totalIncome || 0,
        monthly_income: txStore.summary.totalIncome || 0,
        period: selectedPeriodType.value === 'month' ? 'month' : 'quarter'
      }
    });
    taxData.value = res.data.taxes;
    taxWarnings.value = res.data.warnings;
    paymentCalendar.value = res.data.calendar;
  } catch (e) {
    console.error("Tax Calculation error:", e);
  }
};

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
    txStore.fetchLifetimeSummary(),
    profile.value?.is_fop ? fetchTaxAnalysis() : Promise.resolve()
  ]);
  isPageLoading.value = false;
};

// Реактивність: перераховуємо податки при зміні доходу
watch(() => txStore.summary.totalIncome, () => {
  if (profile.value?.is_fop) fetchTaxAnalysis();
});

const monthName = computed(() => {
  return new Intl.DateTimeFormat('uk-UA', { month: 'long' }).format(new Date(currentYear.value, currentMonth.value));
});

// Обчислення податків на основі даних з API
const taxCalculations = computed(() => {
  if (!taxData.value) return { total: 0, ep: 0, esv: 0, vz: 0 };
  
  return {
    ep: taxData.value.single_tax,
    vz: taxData.value.military_tax,
    esv: taxData.value.esv,
    total: taxData.value.total_monthly_tax
  };
});

// Реальний баланс за весь час (Після податків)
// Використовуємо дані з API для точності
const realBalance = computed(() => {
  const grossBalance = txStore.lifetimeSummary.balance;
  if (!profile.value?.is_fop || !taxData.value) return grossBalance;

  // Рахуємо податки за весь період діяльності
  const monthsCount = txStore.lifetimeSummary.monthsCount || 1;
  const totalIncome = txStore.lifetimeSummary.totalIncome || 0;
  
  const tax = APP_CONSTANTS.TAX_2025;
  let ep = 0;
  let vz = 0;
  const esv = monthsCount * tax.ESV_MONTHLY;

  if (settings.value?.fop_group === 3) {
    const rate = settings.value?.is_vat_payer ? tax.GROUP_3_RATE_VAT : tax.GROUP_3_RATE;
    ep = totalIncome * rate;
    vz = totalIncome * tax.GROUP_3_MILITARY_RATE;
  } else if (settings.value?.fop_group === 4) {
    // В спрощеному варіанті для G4 рахуємо фіксований ВЗ
    ep = monthsCount * 0; // Спрощено, бо G4 залежить від оцінки землі
    vz = monthsCount * tax.FIXED_MILITARY_TAX;
  } else {
    // Для груп 1, 2
    const singleTaxRate = settings.value?.fop_group === 1 ? tax.SINGLE_TAX_G1 : tax.SINGLE_TAX_G2;
    ep = monthsCount * singleTaxRate;
    vz = monthsCount * tax.FIXED_MILITARY_TAX;
  }

  return grossBalance - (ep + vz + esv);
});

// Чистий дохід після податків (поточний період)
const realProfit = computed(() => {
  if (!profile.value?.is_fop || !taxData.value) return txStore.summary.netProfit;
  return txStore.summary.netProfit - taxData.value.total_monthly_tax;
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
  <div class="max-w-6xl mx-auto p-4 sm:p-8 animate-fade-in space-y-8">
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

    <!-- Tax Warnings -->
    <div v-if="taxWarnings.length > 0" class="animate-slide-up space-y-3">
      <div v-for="w in taxWarnings" :key="w" class="p-4 bg-amber-50 border-2 border-amber-100 rounded-2xl flex items-center gap-4 text-amber-900">
        <div class="bg-amber-100 p-2 rounded-xl">
          <Info :size="20" class="text-amber-600" />
        </div>
        <div class="flex-grow">
          <p class="font-black text-sm uppercase tracking-widest" v-if="w === 'LIMIT_APPROACHING'">Наближення ліміту доходу</p>
          <p class="font-black text-sm uppercase tracking-widest" v-else-if="w === 'VAT_REGISTRATION_REQUIRED'">Необхідна реєстрація ПДВ</p>
          <p class="text-xs font-medium opacity-80" v-if="w === 'LIMIT_APPROACHING'">Ви використали понад 90% річного ліміту вашої групи. Стежте за наступними поступленнями.</p>
          <p class="text-xs font-medium opacity-80" v-else-if="w === 'VAT_REGISTRATION_REQUIRED'">Річний дохід перевищив 1 млн грн. Ви повинні зареєструватися платником ПДВ.</p>
        </div>
      </div>
    </div>

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
      <div v-if="profile?.is_fop" class="lg:col-span-1 space-y-6">
        <TaxWidget 
          :calculations="taxCalculations" 
          :settings="settings" 
          :loading="isPageLoading || !settings"
        />

        <!-- Payment Calendar Widget (Hidden for now) -->
        <div v-if="false" class="bg-white rounded-[2rem] shadow-xl shadow-gray-200/50 border border-gray-100 p-8">
            <h3 class="text-xl font-black text-gray-900 mb-6 flex items-center gap-3">
                <Clock class="w-6 h-6 text-blue-600" />
                Календар оплат
            </h3>
            <div class="space-y-4">
                <div v-for="(event, idx) in paymentCalendar" :key="idx" class="flex gap-4 p-4 rounded-2xl bg-gray-50 border border-transparent hover:border-blue-100 transition-all">
                    <div class="w-1 h-full bg-blue-500 rounded-full"></div>
                    <div>
                        <p class="text-xs font-black text-gray-400 uppercase tracking-widest leading-none mb-1">{{ event.deadline }}</p>
                        <p class="font-black text-gray-800 leading-tight">{{ event.event }}</p>
                        <p class="text-[10px] font-bold text-gray-500 uppercase tracking-tight mt-1">Група: {{ event.group }}</p>
                    </div>
                </div>
                <div v-if="paymentCalendar.length === 0" class="text-center py-6 text-gray-400 italic text-sm">
                    Календар завантажується...
                </div>
            </div>
        </div>
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