<script setup>
import { onMounted, computed, ref, watch } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import api from '@/services/api';
import { supabase } from '@/services/supabase';
import { APP_CONSTANTS } from '@/constants/appConstants';
import { useTaxRulesStore } from '@/stores/taxRulesStore';
import { formatMoney } from '@/utils/format';

const taxRulesStore = useTaxRulesStore();

// Імпорти компонентів (тепер використовуємо Tailwind-стилізовані версії, якщо вони будуть)
// Для StatCard та TaxWidget ми можемо або створити нові, або адаптувати існуючі.
// Тут я припускаю, що ми використовуємо їх прямо в шаблоні або імпортуємо оновлені версії.
import StatCard from '@/components/dashboard/StatCard.vue';
import TaxWidget from '@/components/dashboard/TaxWidget.vue';
import DashboardCollapsibleSection from '@/components/dashboard/DashboardCollapsibleSection.vue';
import TransactionModal from '@/components/dashboard/TransactionModal.vue';
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import TransactionFormModal from '@/components/transactions/TransactionFormModal.vue';
import CategoryModal from '@/components/common/CategoryModal.vue';
import { ArrowDownLeft, ArrowUpRight, Calculator, Info, CreditCard, User, Plus } from 'lucide-vue-next';
import { useTransactionActions } from '@/actions/useTransactionActions';

const txStore = useTransactionStore();
const profile = ref(null);
const userId = ref(null);
const isPageLoading = ref(true);
const taxData = ref(null);
const taxWarnings = ref([]);

// Transaction logic from centralized composable
const {
  isModalOpen,
  isCategoryModalOpen,
  isSubmitting,
  editingTxId,
  fopSettings,
  isDetailModalOpen,
  selectedTransaction,
  form,
  openCreateModal,
  openTransactionDetails,
  submitTransaction,
  handleTransactionUpdate,
  fetchFopSettings
} = useTransactionActions(userId, async () => {
  const filters = getPeriodFilters();
  await Promise.all([
    txStore.fetchTransactions(filters),
    txStore.fetchLifetimeSummary(filters.endDate)
  ]);
  if (profile.value?.is_fop) {
    await fetchTaxAnalysis();
  }
});

// Фільтрація періоду
const currentDate = new Date();
const currentMonth = ref(currentDate.getMonth());
const currentYear = ref(currentDate.getFullYear());
const selectedPeriodType = ref('month'); // 'month' або 'custom'

// Ініціалізація періоду (поточний місяць)
const getPeriodFilters = () => {
  const { start, end } = txStore.getMonthRange(currentYear.value, currentMonth.value);
  return { startDate: start, endDate: end, type: '', categoryId: '' };
};

onMounted(async () => {
  isPageLoading.value = true;
  const { data: { user } } = await supabase.auth.getUser();
  if (user) {
    userId.value = user.id;
    
    try {
      const filters = getPeriodFilters();

      // Завантажуємо все паралельно для швидкості
      const [profileRes] = await Promise.all([
        api.getProfile(user.id),
        txStore.fetchInitialData(filters)
      ]);
      
      profile.value = profileRes.data;

      // Якщо ФОП - тягнемо налаштування та розрахунок податків
      if (profile.value?.is_fop) {
        await Promise.all([
          fetchFopSettings(),
          taxRulesStore.fetchRules(currentYear.value, currentMonth.value + 1)
        ]);
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
        annual_income: txStore.lifetimeSummary.totalFopIncome || 0,
        monthly_income: txStore.summary.totalFopIncome || 0,
        period: selectedPeriodType.value === 'month' ? 'month' : 'quarter',
        calc_date: `${currentYear.value}-${String(currentMonth.value + 1).padStart(2, '0')}-01`
      }
    });
    taxData.value = res.data.taxes;
    taxWarnings.value = res.data.warnings;
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
  
  const filters = getPeriodFilters();
  
  // Спочатку чекаємо на оновлення транзакцій, щоб мати актуальний дохід для податків
  await Promise.all([
    txStore.fetchTransactions(filters),
    txStore.fetchLifetimeSummary(filters.endDate)
  ]);
  
  if (profile.value?.is_fop) {
    await Promise.all([
      fetchTaxAnalysis(),
      taxRulesStore.fetchRules(currentYear.value, currentMonth.value + 1)
    ]);
  }
  
  isPageLoading.value = false;
};

// Реактивність: перераховуємо податки при зміні доходу
watch(() => txStore.summary.totalFopIncome, () => {
  if (profile.value?.is_fop) fetchTaxAnalysis();
});

const monthName = computed(() => {
  return new Intl.DateTimeFormat('uk-UA', { month: 'long' }).format(new Date(currentYear.value, currentMonth.value));
});

const analyticsTransactionsLink = computed(() => {
  const filters = getPeriodFilters();
  const currentMonthRange = txStore.getMonthRange();
  const now = new Date();
  const lastMonthRange = txStore.getMonthRange(
    now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear(),
    now.getMonth() === 0 ? 11 : now.getMonth() - 1
  );

  let period = 'custom';
  if (filters.startDate === currentMonthRange.start && filters.endDate === currentMonthRange.end) {
    period = 'this_month';
  } else if (filters.startDate === lastMonthRange.start && filters.endDate === lastMonthRange.end) {
    period = 'last_month';
  }

  return {
    path: '/analytics',
    query: {
      tab: 'transactions',
      period,
      startDate: filters.startDate,
      endDate: filters.endDate
    }
  };
});

// Обчислення податків на основі даних з API
const taxCalculations = computed(() => {
  if (!taxData.value) return { total: 0, ep: 0, esv: 0, vz: 0 };
  
  const ep = taxData.value.single_tax || 0;
  const vz = taxData.value.military_tax || 0;
  const esv = taxData.value.esv || 0;

  return {
    ep,
    vz,
    esv,
    total: (ep + vz + esv)
  };
});

const taxAccrualPeriodLabel = computed(() => {
  return selectedPeriodType.value === 'month' ? 'місяць' : 'квартал';
});

// Реальний баланс за весь час (Після податків)
// Примітка: Це оціночне значення, оскільки ми не рахуємо кожен історичний місяць окремо на фронті.
const realBalance = computed(() => {
  const grossBalance = txStore.lifetimeSummary.balance;
  if (!profile.value?.is_fop) return grossBalance;

  // Якщо у нас немає розширених даних, повертаємо валовий баланс
  // В майбутньому тут можна додати запит на /analytics/history/taxes для точного балансу
  return grossBalance;
});

// Чистий дохід після податків (поточний період)
const realProfit = computed(() => {
  if (!profile.value?.is_fop || !taxData.value) return txStore.summary.netProfit;
  return txStore.summary.netProfit - taxCalculations.value.total;
});

// Отримання назви категорії (допоміжна функція)
const getCategoryName = (id) => {
  return txStore.getCategoryName(id);
};
</script>

<template>
  <div class="max-w-6xl mx-auto p-4 sm:p-8 animate-fade-in space-y-5 lg:space-y-8 pb-28 lg:pb-8">
    <!-- Header with Period Selector -->
    <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 lg:gap-6 mb-0 lg:mb-2">
      <div>
        <h1 class="text-2xl sm:text-3xl font-black text-gray-900 tracking-tight">Фінансовий огляд</h1>
        <p class="text-gray-500 font-medium mt-1 text-sm sm:text-base hidden sm:block">Огляд вашої активності за обраний період</p>
      </div>

      <!-- Month Selector -->
      <div class="flex items-center bg-white border border-gray-100 rounded-2xl p-1.5 shadow-sm w-full sm:w-auto">
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

    <!-- Mobile: balance + collapsible funds & tax -->
    <div class="lg:hidden space-y-3">
      <div class="bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-5 text-white shadow-lg shadow-blue-200/40">
        <p class="text-[10px] font-black uppercase tracking-widest text-blue-200">
          Загальний баланс
        </p>
        <SkeletonLoader
          v-if="isPageLoading"
          width="160px"
          height="36px"
          className="bg-white/20 mt-2"
          borderRadius="10px"
        />
        <p v-else class="text-3xl font-black mt-1 tabular-nums whitespace-nowrap">
          {{ formatMoney(realBalance) }}
        </p>
        <p class="text-sm text-blue-200 mt-1">
          {{ profile?.is_fop ? 'Прибуток за весь час' : 'Всього за весь час' }}
        </p>
      </div>

      <DashboardCollapsibleSection title="Кошти за період">
        <template #summary>
          <SkeletonLoader v-if="isPageLoading" width="120px" height="28px" borderRadius="8px" />
          <template v-else>
            <p class="text-xl font-black text-gray-900 tabular-nums whitespace-nowrap">
              {{ formatMoney(realProfit) }}
            </p>
            <p class="text-xs text-gray-500 mt-0.5 capitalize">
              Прибуток · {{ monthName }} {{ currentYear }}
            </p>
          </template>
        </template>

        <div class="space-y-3">
          <div class="flex justify-between items-center gap-3 py-2 border-b border-gray-50">
            <div class="min-w-0">
              <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Поступлення</p>
              <p v-if="profile?.is_fop" class="text-xs text-blue-600 font-semibold mt-0.5 truncate">
                ФОП: {{ formatMoney(txStore.summary.totalFopIncome) }}
              </p>
            </div>
            <SkeletonLoader v-if="isPageLoading" width="80px" height="20px" />
            <span v-else class="font-black text-blue-600 tabular-nums whitespace-nowrap shrink-0">
              {{ formatMoney(txStore.summary.totalIncome) }}
            </span>
          </div>
          <div class="flex justify-between items-center gap-3 py-2 border-b border-gray-50">
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Витрати</p>
            <SkeletonLoader v-if="isPageLoading" width="80px" height="20px" />
            <span v-else class="font-black text-red-500 tabular-nums whitespace-nowrap shrink-0">
              {{ formatMoney(txStore.summary.totalExpense) }}
            </span>
          </div>
          <div class="flex justify-between items-center gap-3 py-2">
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
              {{ profile?.is_fop ? 'Прибуток після податків' : 'Прибуток' }}
            </p>
            <SkeletonLoader v-if="isPageLoading" width="80px" height="20px" />
            <span v-else class="font-black text-gray-900 tabular-nums whitespace-nowrap shrink-0">
              {{ formatMoney(realProfit) }}
            </span>
          </div>
        </div>
      </DashboardCollapsibleSection>

      <DashboardCollapsibleSection
        v-if="profile?.is_fop"
        title="Податковий розрахунок"
      >
        <template #summary>
          <SkeletonLoader v-if="isPageLoading || !fopSettings" width="120px" height="28px" borderRadius="8px" />
          <template v-else>
            <p class="text-xl font-black text-indigo-900 tabular-nums whitespace-nowrap">
              {{ taxCalculations.total.toFixed(2) }}&nbsp;₴
            </p>
            <p class="text-xs text-gray-500 mt-0.5">
              Нараховано за {{ taxAccrualPeriodLabel }}
              <span v-if="fopSettings?.fop_group"> · ФОП {{ fopSettings.fop_group }}-ї групи</span>
            </p>
          </template>
        </template>

        <TaxWidget
          embedded
          :calculations="taxCalculations"
          :settings="fopSettings"
          :period-label="taxAccrualPeriodLabel"
          :loading="isPageLoading || !fopSettings"
        />
      </DashboardCollapsibleSection>
    </div>

    <!-- Stats Grid (desktop / tablet landscape) -->
    <div class="hidden lg:grid grid-cols-2 xl:grid-cols-4 gap-6">
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
        :fopAmount="formatMoney(txStore.summary.totalFopIncome)"
        subtext="За вибраний місяць"
        variant="white"
        amountColor="blue"
        :loading="isPageLoading"
        :showFopLoading="profile?.is_fop"
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
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
      
      <!-- Tax Widget Column (Only for FOP, desktop) -->
      <div v-if="profile?.is_fop" class="hidden lg:block lg:col-span-1 space-y-6">
        <TaxWidget 
          :calculations="taxCalculations" 
          :settings="fopSettings" 
          :period-label="taxAccrualPeriodLabel"
          :loading="isPageLoading || !fopSettings"
        />
      </div>

      <!-- Recent Transactions List Column -->
      <div class="lg:col-span-2 bg-white rounded-2xl lg:rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div class="p-4 border-b flex justify-between items-center gap-3 bg-gray-50">
          <h2 class="font-bold text-gray-800 text-base sm:text-lg">Останні операції</h2>
          <router-link :to="analyticsTransactionsLink" class="text-sm text-blue-600 font-medium hover:text-blue-800 transition-colors">
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
          <li 
            v-for="tx in txStore.transactions.slice(0, 5)" 
            :key="tx.transaction_id" 
            @click="openTransactionDetails(tx)"
            class="p-4 hover:bg-gray-50 transition-colors flex justify-between items-center gap-3 cursor-pointer group"
          >
            
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <!-- Icon based on type -->
              <div :class="['p-2 rounded-full shrink-0 transition-transform group-hover:scale-110', tx.transaction_type === 'income' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600']">
                <component 
                  :is="tx.transaction_type === 'income' ? ArrowDownLeft : ArrowUpRight" 
                  class="w-5 h-5"
                />
              </div>
              
              <div class="min-w-0">
                <span class="block font-medium text-gray-800 truncate">
                  {{ getCategoryName(tx.category_id) }}
                </span>
                <span class="text-xs text-gray-500">
                  {{ new Date(tx.transaction_date).toLocaleDateString('uk-UA') }}
                </span>
              </div>
            </div>

            <div class="text-right shrink-0">
              <div :class="['font-bold tabular-nums whitespace-nowrap', tx.transaction_type === 'income' ? 'text-green-600' : 'text-gray-900']">
                {{ tx.transaction_type === 'income' ? '+' : '-' }}{{ tx.transaction_amount.toFixed(2) }}&nbsp;₴
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

    <!-- Transaction Detail Modal -->
    <TransactionModal 
      :isOpen="isDetailModalOpen"
      :transaction="selectedTransaction"
      :userId="userId"
      :fopSettings="fopSettings"
      @close="isDetailModalOpen = false; selectedTransaction = null"
      @updated="handleTransactionUpdate"
      @deleted="handleTransactionUpdate"
    />

    <!-- Transaction Form Modal -->
    <TransactionFormModal 
      :isOpen="isModalOpen"
      :editingTxId="editingTxId"
      v-model:form="form"
      :fopSettings="fopSettings"
      :isSubmitting="isSubmitting"
      @close="isModalOpen = false"
      @submit="submitTransaction"
      @add-category="isCategoryModalOpen = true"
    />

    <CategoryModal 
      v-if="isCategoryModalOpen"
      :isOpen="isCategoryModalOpen"
      :userId="userId"
      :type="form.type"
      @close="isCategoryModalOpen = false"
      @saved="isCategoryModalOpen = false"
    />

    <!-- Floating Action Button: Add Transaction -->
    <button 
      @click="openCreateModal"
      class="fixed z-50 bg-blue-600 hover:bg-blue-700 text-white font-black transition-all shadow-2xl shadow-blue-300 flex items-center justify-center gap-3 hover:scale-110 active:scale-95 group w-16 h-16 md:w-auto md:h-auto md:py-4 md:px-8 rounded-full md:rounded-2xl bottom-[max(1.5rem,env(safe-area-inset-bottom))] right-[max(1rem,env(safe-area-inset-right))] sm:bottom-8 sm:right-8"
    >
      <div class="flex items-center justify-center group-hover:rotate-90 transition-transform duration-300">
        <Plus :size="24" stroke-width="3" />
      </div>
      <span class="hidden md:inline text-lg">Додати запис</span>
    </button>
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