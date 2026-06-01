<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useTransactionStore } from '@/stores/transactionStore';
import { Doughnut, Line, Bar } from 'vue-chartjs';
import { 
  Chart as ChartJS, 
  Title, 
  Tooltip, 
  Legend, 
  ArcElement, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  BarElement,
  Filler
} from 'chart.js';
import { PieChart, ArrowUpRight, ArrowDownLeft, TrendingUp, BarChart3, CalendarDays, Loader2, Plus, History } from 'lucide-vue-next';
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import TransactionFilters from '@/components/transactions/TransactionFilters.vue';
import BudgetCard from '@/components/analytics/BudgetCard.vue';
import BudgetForm from '@/components/analytics/BudgetForm.vue';
import TransactionList from '@/components/transactions/TransactionList.vue';
import TransactionFormModal from '@/components/transactions/TransactionFormModal.vue';
import CategoryModal from '@/components/common/CategoryModal.vue';
import TransactionModal from '@/components/dashboard/TransactionModal.vue';
import ExportCsvPanel from '@/components/analytics/ExportCsvPanel.vue';
import FopGroupRecommendPanel from '@/components/analytics/FopGroupRecommendPanel.vue';
import { useBudgetStore } from '@/stores/budgetStore';
import { supabase } from '@/services/supabase';
import api from '@/services/api';
import { useTransactionActions } from '@/actions/useTransactionActions';

ChartJS.register(
  Title, Tooltip, Legend, ArcElement, CategoryScale, 
  LinearScale, PointElement, LineElement, BarElement, Filler
);

const store = useTransactionStore();
const budgetStore = useBudgetStore();
const router = useRouter();
const route = useRoute();

const activeTab = ref('overview');
const isBudgetFormOpen = ref(false);
const budgetToEdit = ref(null);
const isSyncingTax = ref(false);
const isFilterTransitionLoading = ref(false);

const userId = ref(null);

const isValidIsoDate = (value) => {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
};

const pickQuery = (key) => {
  const v = route.query[key];
  if (Array.isArray(v)) return v[0];
  return v;
};

const getFiltersFromQuery = () => {
  const out = {};
  const startDate = pickQuery('startDate');
  const endDate = pickQuery('endDate');
  if (isValidIsoDate(startDate) && isValidIsoDate(endDate)) {
    out.startDate = startDate;
    out.endDate = endDate;
  }

  const period = pickQuery('period');
  const allowedPeriods = new Set([
    '',
    'today',
    'yesterday',
    'last_week',
    'last_two_weeks',
    'this_month',
    'last_month',
    'last_3_months',
    'custom'
  ]);
  if (period !== undefined && period !== null && allowedPeriods.has(String(period))) {
    out.period = period === '' ? '' : String(period);
  }

  const type = pickQuery('type');
  if (type === 'income' || type === 'expense') out.type = type;
  else if (type === 'all' || type === '') out.type = '';

  const category = pickQuery('category');
  if (category !== undefined && category !== null && String(category).length > 0) {
    out.categoryId = String(category);
  }

  const q = pickQuery('q');
  if (typeof q === 'string') {
    out.searchText = q;
  }

  return out;
};

const filtersMatchRouteQuery = () => {
  const f = store.filters;
  return (
    (f.startDate || '') === String(pickQuery('startDate') || '') &&
    (f.endDate || '') === String(pickQuery('endDate') || '') &&
    String(f.period ?? '') === String(pickQuery('period') ?? '') &&
    (f.type || '') === String(pickQuery('type') || '') &&
    (f.categoryId || '') === String(pickQuery('category') || '') &&
    (f.searchText || '') === String(pickQuery('q') || '')
  );
};

const buildRouteQueryFromFilters = () => {
  const f = store.filters;
  const next = { ...route.query, tab: activeTab.value };
  next.startDate = f.startDate || undefined;
  next.endDate = f.endDate || undefined;
  if (f.period !== undefined && f.period !== '') {
    next.period = f.period;
  } else {
    delete next.period;
  }
  next.type = f.type || undefined;
  next.category = f.categoryId || undefined;
  next.q = f.searchText || undefined;
  return Object.fromEntries(
    Object.entries(next).filter(([, v]) => v !== undefined && v !== '')
  );
};

let pushingFiltersToRoute = false;

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
  await store.fetchTransactions();
  await budgetStore.fetchBudgetProgress();
});

onMounted(async () => {
  // Check for tab in query
  if (route.query.tab) {
    const tab = String(route.query.tab);
    activeTab.value = tab === 'calendar' ? 'overview' : tab;
  }

  const { data: { user } } = await supabase.auth.getUser();
  if (user) {
    userId.value = user.id;
    // Fetch settings for transaction form
    await fetchFopSettings();
  }

  const queryPartial = getFiltersFromQuery();
  if (Object.keys(queryPartial).length > 0) {
    isFilterTransitionLoading.value = true;
    store.filters = { ...store.filters, ...queryPartial };
  }

  // Fetch everything needed for analytics
  await Promise.all([
    store.fetchInitialData(null),
    budgetStore.fetchBudgetProgress(),
    budgetStore.fetchTaxHistory()
  ]);

  if (activeTab.value === 'reports' && store.filters.startDate && store.filters.endDate) {
    await budgetStore.fetchBehaviorInsights(store.filters.startDate, store.filters.endDate);
  }

  isFilterTransitionLoading.value = false;
});

const submitNewCategory = async () => {
  isCategoryModalOpen.value = false;
};

// Sync tab with query
watch(() => route.query.tab, (newTab) => {
  if (!newTab) return;
  const tab = String(newTab);
  activeTab.value = tab === 'calendar' ? 'overview' : tab;
});

watch(
  () => route.query,
  async () => {
    if (pushingFiltersToRoute) return;
    const partial = getFiltersFromQuery();
    if (!Object.keys(partial).length) return;
    isFilterTransitionLoading.value = true;
    store.filters = { ...store.filters, ...partial };
    await nextTick();
    isFilterTransitionLoading.value = false;
  },
  { deep: true }
);

watch(activeTab, (newTab) => {
  router.replace({ query: { ...route.query, tab: newTab } });
  if (newTab === 'history') {
    budgetStore.fetchTaxHistory();
  }
  if (newTab === 'reports') {
    budgetStore.fetchBehaviorInsights(store.filters.startDate, store.filters.endDate);
  }
});

const openBudgetForm = (budget = null) => {
  budgetToEdit.value = budget;
  isBudgetFormOpen.value = true;
};

const closeBudgetForm = () => {
  isBudgetFormOpen.value = false;
  budgetToEdit.value = null;
};

const deleteBudget = async (id) => {
  if (confirm('Видалити цей бюджет?')) {
    const { data: { user } } = await supabase.auth.getUser();
    await budgetStore.deleteBudget(id, user.id);
  }
};

const syncAllHistory = async () => {
  isSyncingTax.value = true;
  try {
    await budgetStore.syncAllTaxes();
  } catch (e) {
    console.error("Sync error", e);
  } finally {
    isSyncingTax.value = false;
  }
};

watch(
  () => store.filters,
  async (newFilters) => {
    store.fetchTransactions();

    if (activeTab.value === 'reports') {
      budgetStore.fetchBehaviorInsights(newFilters.startDate, newFilters.endDate);
    }

    if (pushingFiltersToRoute) return;
    if (filtersMatchRouteQuery()) return;
    pushingFiltersToRoute = true;
    await router.replace({ query: buildRouteQueryFromFilters() });
    await nextTick();
    pushingFiltersToRoute = false;
  },
  { deep: true }
);

const resetFilters = () => {
  const { start, end } = store.getMonthRange();
  store.filters = { startDate: start, endDate: end, type: '', categoryId: '', period: 'this_month', searchText: '' };
};

// Helper to accumulate amounts by category
const getChartData = (type) => {
  if (!store.transactions) return { labels: [], datasets: [{ data: [], backgroundColor: [] }], catIds: [] };
  const filtered = store.transactions.filter(t => t.transaction_type === type);
  const categoryTotals = {};
  
  filtered.forEach(tx => {
    const catName = store.getCategoryName(tx.category_id);
    const amount = parseFloat(tx.transaction_amount);
    if (!categoryTotals[catName]) {
      categoryTotals[catName] = { amount: 0, id: tx.category_id };
    }
    categoryTotals[catName].amount += amount;
  });

  const labels = Object.keys(categoryTotals);
  const data = Object.values(categoryTotals).map(c => c.amount);
  const catIds = Object.values(categoryTotals).map(c => c.id);

  // Generate some nice colors
  const baseColors = type === 'expense' 
    ? ['#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1']
    : ['#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#4f46e5', '#8b5cf6'];

  const backgroundColor = labels.map((_, i) => baseColors[i % baseColors.length]);

  return {
    labels,
    datasets: [{
      data,
      backgroundColor,
      borderWidth: 0,
      hoverOffset: 8
    }],
    catIds
  };
};

const expenseData = computed(() => getChartData('expense'));
const incomeData = computed(() => getChartData('income'));

// --- New Time Series Data Logic ---

const selectedTrendCategoryId = ref('');

// Get all unique dates from transactions, sorted
const chartLabels = computed(() => {
  if (!store.transactions || store.transactions.length === 0) return [];
  const dates = [...new Set(store.transactions.map(t => t.transaction_date))];
  return dates.sort((a, b) => new Date(a) - new Date(b));
});

// Helper to group transactions by date and type
const getGroupedByDate = (type, categoryId = null) => {
  const grouped = {};
  if (!store.transactions) return {};
  store.transactions.forEach(tx => {
    if (type && tx.transaction_type !== type) return;
    if (categoryId && tx.category_id !== categoryId) return;
    
    const date = tx.transaction_date;
    const amount = parseFloat(tx.transaction_amount);
    grouped[date] = (grouped[date] || 0) + amount;
  });
  return grouped;
};

const expenseTrendData = computed(() => {
  const grouped = getGroupedByDate('expense');
  const data = chartLabels.value.map(date => grouped[date] || 0);

  return {
    labels: chartLabels.value,
    datasets: [{
      label: 'Витрати',
      data,
      borderColor: '#ef4444',
      backgroundColor: 'rgba(239, 68, 68, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
      borderWidth: 3
    }]
  };
});

const comparisonData = computed(() => {
  const incomeGrouped = getGroupedByDate('income');
  const expenseGrouped = getGroupedByDate('expense');
  
  const incomeDataPoints = chartLabels.value.map(date => incomeGrouped[date] || 0);
  const expenseDataPoints = chartLabels.value.map(date => expenseGrouped[date] || 0);

  return {
    labels: chartLabels.value,
    datasets: [
      {
        label: 'Доходи',
        data: incomeDataPoints,
        backgroundColor: '#22c55e',
        borderRadius: 8,
      },
      {
        label: 'Витрати',
        data: expenseDataPoints,
        backgroundColor: '#ef4444',
        borderRadius: 8,
      }
    ]
  };
});

const categoryTrendData = computed(() => {
  if (!selectedTrendCategoryId.value) return null;
  
  const grouped = getGroupedByDate(null, selectedTrendCategoryId.value);
  const data = chartLabels.value.map(date => grouped[date] || 0);
  const catName = store.getCategoryName(selectedTrendCategoryId.value);

  return {
    labels: chartLabels.value,
    datasets: [{
      label: catName,
      data,
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
      borderWidth: 3
    }]
  };
});

// Watch for categories to select a default trend category
watch(() => store.categories.all, (newCats) => {
  if (newCats && newCats.length > 0 && !selectedTrendCategoryId.value) {
    // Prefer "Salary" or first income category, else first available
    const salary = newCats.find(c => c.name.toLowerCase().includes('зарплат') || c.name.toLowerCase().includes('salary'));
    if (salary) {
      selectedTrendCategoryId.value = salary.id;
    } else {
      selectedTrendCategoryId.value = newCats[0].id;
    }
  }
}, { immediate: true });

// New Point/Bar click handler for Time Series
const handleTimePointClick = (event, elements, type) => {
  if (!elements.length) return;
  const index = elements[0].index;
  const date = chartLabels.value[index];
  
  // Set date filters to that specific day
  store.filters.startDate = date;
  store.filters.endDate = date;
  
  if (type === 'income' || type === 'expense') {
    store.filters.type = type;
  }
  
  // If it's the category trend chart, also filter by category
  if (type === 'category') {
    store.filters.categoryId = selectedTrendCategoryId.value;
  }

  router.push('/transactions');
};

// Chart click handler for Doughnut charts
const handleChartClick = (type, elements) => {
  if (!elements.length) return;
  const index = elements[0].index;
  const chartData = type === 'expense' ? expenseData.value : incomeData.value;
  const categoryId = chartData.catIds[index];
  
  // Set filter in store
  store.filters.type = type;
  store.filters.categoryId = categoryId;
  
  // Navigate to transactions 
  router.push('/transactions');
};

const commonOptions = (type) => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '70%',
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        usePointStyle: true,
        padding: 24,
        font: {
          family: 'Inter, sans-serif',
          size: 13,
          weight: '600'
        },
        color: '#4b5563'
      }
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          let label = context.label || '';
          if (label) label += ': ';
          if (context.parsed !== null) {
            label += new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(context.parsed);
          }
           return label;
        },
        footer: () => 'Натисніть, щоб переглянути категорію'
      },
      padding: 16,
      cornerRadius: 16,
      backgroundColor: 'rgba(17, 24, 39, 0.9)',
      titleFont: { size: 14, family: 'Inter, sans-serif', weight: 'bold' },
      bodyFont: { size: 14, font: 'Inter, sans-serif', weight: 'bold' }
    }
  },
  onClick: (event, elements) => handleChartClick(type, elements),
  onHover: (event, elements) => {
    event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
  }
});

const areaOptions = {
  responsive: true,
  maintainAspectRatio: false,
  onClick: (event, elements) => handleTimePointClick(event, elements, 'expense'),
  onHover: (event, elements) => {
    event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      mode: 'index',
      intersect: false,
      padding: 16,
      cornerRadius: 16,
      backgroundColor: 'rgba(17, 24, 39, 0.9)',
      titleFont: { size: 14, family: 'Inter, sans-serif', weight: 'bold' },
      bodyFont: { size: 14, font: 'Inter, sans-serif' },
      callbacks: {
        label: (context) => {
          let label = context.dataset.label || '';
          if (label) label += ': ';
          if (context.parsed.y !== null) {
            label += new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(context.parsed.y);
          }
          return label;
        },
        footer: () => 'Натисніть, щоб переглянути деталі'
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        font: { family: 'Inter, sans-serif', size: 11 },
        maxRotation: 45,
        minRotation: 45
      }
    },
    y: {
      beginAtZero: true,
      grid: { color: '#f3f4f6' },
      ticks: {
        font: { family: 'Inter, sans-serif', size: 11 },
        callback: (value) => new Intl.NumberFormat('uk-UA', { notation: 'compact' }).format(value)
      }
    }
  }
};

const barOptions = {
  ...areaOptions,
  onClick: (event, elements) => {
    if (!elements.length) return;
    const datasetIndex = elements[0].datasetIndex;
    const type = datasetIndex === 0 ? 'income' : 'expense';
    handleTimePointClick(event, elements, type);
  },
  plugins: {
    ...areaOptions.plugins,
    legend: {
      display: true,
      position: 'top',
      labels: { usePointStyle: true, padding: 20, font: { weight: '600' } }
    }
  }
};

const categoryAreaOptions = {
  ...areaOptions,
  onClick: (event, elements) => handleTimePointClick(event, elements, 'category')
};

const severityBadgeClass = (severity) => {
  if (severity === 'high') return 'bg-red-100 text-red-700 border-red-200';
  if (severity === 'medium') return 'bg-amber-100 text-amber-700 border-amber-200';
  return 'bg-emerald-100 text-emerald-700 border-emerald-200';
};

const severityLabel = (severity) => {
  if (severity === 'high') return 'високий';
  if (severity === 'medium') return 'середній';
  return 'низький';
};

const openCategoryTransactions = (categoryId) => {
  store.filters.categoryId = categoryId === 'uncategorized' ? '' : categoryId;
  store.filters.type = 'expense';
  activeTab.value = 'transactions';
};

const exportYear = computed(() => {
  const sd = store.filters.startDate;
  if (sd && /^\d{4}/.test(sd)) return parseInt(sd.slice(0, 4), 10);
  return new Date().getFullYear();
});

const analyticsTabs = [
  { id: 'overview', label: 'Огляд' },
  { id: 'transactions', label: 'Транзакції' },
  { id: 'fop_group', label: 'Група ФОП' },
  { id: 'budgets', label: 'Бюджети' },
  { id: 'history', label: 'Історія податків' },
  { id: 'reports', label: 'Аналіз поведінки' },
];
</script>

<template>
  <div class="max-w-6xl mx-auto p-4 sm:p-8 animate-fade-in font-sans">
    <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8 sm:mb-12">
      <div>
        <h1 class="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight flex items-center gap-3">
          <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-100/50">
             <PieChart :size="24" stroke-width="3" />
          </div>
          Аналітика
        </h1>
        <p class="text-gray-500 font-medium mt-2 text-lg">Управління бюджетами та розширені звіти</p>
      </div>
    </header>

    <!-- Tabs Navigation -->
    <div class="flex flex-wrap gap-2 mb-8 bg-gray-100/50 p-2 rounded-[2rem] max-w-fit">
      <button 
        v-for="tab in analyticsTabs" 
        :key="tab.id"
        @click="activeTab = tab.id"
        class="px-6 py-3 rounded-3xl font-bold transition-all duration-300 outline-none"
        :class="activeTab === tab.id ? 'bg-white text-blue-600 shadow-md transform scale-105' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-200/50'"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Filters Bar - Unified for all tabs -->
    <TransactionFilters 
      v-if="['overview', 'transactions', 'reports'].includes(activeTab) && !isFilterTransitionLoading"
      v-model:filters="store.filters"
      @reset="resetFilters"
    />
    <div
      v-else-if="['overview', 'transactions', 'reports'].includes(activeTab) && isFilterTransitionLoading"
      class="bg-white p-3 sm:p-4 rounded-2xl border border-gray-100 mb-4 sm:mb-8 shadow-md shadow-gray-200/40"
    >
      <div class="flex flex-col min-[480px]:flex-row gap-3 min-[480px]:items-center">
        <SkeletonLoader class="flex-1 min-w-0" height="38px" borderRadius="10px" />
        <div class="flex flex-wrap gap-2 shrink-0">
          <SkeletonLoader width="96px" height="38px" borderRadius="10px" />
          <SkeletonLoader width="140px" height="38px" borderRadius="10px" />
          <SkeletonLoader width="72px" height="38px" borderRadius="10px" />
        </div>
      </div>
    </div>

    <!-- Обгортка для вкладки Огляд -->
    <div v-show="activeTab === 'overview'">

    <div v-if="store.isLoading" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div class="bg-white p-8 rounded-[2.5rem] shadow-2xl shadow-gray-200/50 border border-gray-50 aspect-square flex flex-col items-center">
        <SkeletonLoader width="200px" height="32px" class="mb-12 self-start" />
        <SkeletonLoader width="350px" height="350px" borderRadius="50%" />
      </div>
      <div class="bg-white p-8 rounded-[2.5rem] shadow-2xl shadow-gray-200/50 border border-gray-50 aspect-square flex flex-col items-center">
         <SkeletonLoader width="200px" height="32px" class="mb-12 self-start" />
         <SkeletonLoader width="350px" height="350px" borderRadius="50%" />
      </div>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- Витрати -->
      <div class="bg-white p-6 sm:p-10 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col relative group">
        <div class="flex items-center gap-4 mb-8">
          <div class="w-14 h-14 bg-red-50 text-red-600 rounded-2xl flex items-center justify-center shadow-lg shadow-red-100/50 transform group-hover:-translate-y-1 transition-transform">
            <ArrowDownLeft :size="28" stroke-width="3" />
          </div>
          <div>
            <h2 class="text-2xl font-black text-gray-800 tracking-tight">Загальні витрати</h2>
            <p class="text-sm font-bold text-gray-400 mt-1 uppercase tracking-wider">Структура за категоріями</p>
          </div>
        </div>
        
        <div class="flex-grow relative min-h-[450px]">
          <Doughnut 
            v-if="expenseData.datasets[0].data.length > 0"
            :data="expenseData" 
            :options="commonOptions('expense')" 
          />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 gap-4">
             <PieChart :size="48" stroke-width="1.5" class="opacity-50" />
            <span class="font-black tracking-widest uppercase text-sm">Немає транзакцій</span>
          </div>
        </div>
      </div>

      <!-- Доходи -->
      <div class="bg-white p-6 sm:p-10 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col relative group">
        <div class="flex items-center gap-4 mb-8">
          <div class="w-14 h-14 bg-green-50 text-green-600 rounded-2xl flex items-center justify-center shadow-lg shadow-green-100/50 transform group-hover:-translate-y-1 transition-transform">
            <ArrowUpRight :size="28" stroke-width="3" />
          </div>
           <div>
            <h2 class="text-2xl font-black text-gray-800 tracking-tight">Загальні доходи</h2>
            <p class="text-sm font-bold text-gray-400 mt-1 uppercase tracking-wider">Структура за джерелами</p>
          </div>
        </div>
        
        <div class="flex-grow relative min-h-[450px]">
          <Doughnut 
            v-if="incomeData.datasets[0].data.length > 0"
            :data="incomeData" 
            :options="commonOptions('income')" 
          />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 gap-4">
             <PieChart :size="48" stroke-width="1.5" class="opacity-50" />
            <span class="font-black tracking-widest uppercase text-sm">Немає транзакцій</span>
          </div>
        </div>
      </div>

      <!-- Динаміка витрат (Line Chart) -->
      <div class="bg-white p-6 sm:p-10 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col lg:col-span-2 group">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-100/50 transform group-hover:-translate-y-1 transition-transform">
              <TrendingUp :size="28" stroke-width="3" />
            </div>
            <div>
              <h2 class="text-2xl font-black text-gray-800 tracking-tight">Динаміка витрат</h2>
              <p class="text-sm font-bold text-gray-400 mt-1 uppercase tracking-wider">Зміни витрат у часі</p>
            </div>
          </div>
        </div>
        
        <div class="flex-grow relative min-h-[400px]">
          <Line 
            v-if="expenseTrendData.datasets[0].data.some(v => v > 0)"
            :data="expenseTrendData" 
            :options="areaOptions" 
          />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 gap-4">
            <TrendingUp :size="48" stroke-width="1.5" class="opacity-50" />
            <span class="font-black tracking-widest uppercase text-sm">Недостатньо даних для графіка</span>
          </div>
        </div>
      </div>

      <!-- Порівняння доходів та витрат (Bar Chart) -->
      <div class="bg-white p-6 sm:p-10 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col lg:col-span-2 group">
        <div class="flex items-center gap-4 mb-8">
          <div class="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-100/50 transform group-hover:-translate-y-1 transition-transform">
            <BarChart3 :size="28" stroke-width="3" />
          </div>
          <div>
            <h2 class="text-2xl font-black text-gray-800 tracking-tight">Порівняння</h2>
            <p class="text-sm font-bold text-gray-400 mt-1 uppercase tracking-wider">Доходи проти витрат</p>
          </div>
        </div>
        
        <div class="flex-grow relative min-h-[400px]">
          <Bar 
            v-if="chartLabels.length > 0"
            :data="comparisonData" 
            :options="barOptions" 
          />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 gap-4">
            <BarChart3 :size="48" stroke-width="1.5" class="opacity-50" />
            <span class="font-black tracking-widest uppercase text-sm">Немає транзакцій за цей період</span>
          </div>
        </div>
      </div>

      <!-- Тренд за конкретною категорією -->
      <div class="bg-white p-6 sm:p-10 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col lg:col-span-2 group">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 bg-fuchsia-50 text-fuchsia-600 rounded-2xl flex items-center justify-center shadow-lg shadow-fuchsia-100/50 transform group-hover:-translate-y-1 transition-transform">
              <CalendarDays :size="28" stroke-width="3" />
            </div>
            <div>
              <h2 class="text-2xl font-black text-gray-800 tracking-tight">Аналіз категорії</h2>
              <p class="text-sm font-bold text-gray-400 mt-1 uppercase tracking-wider">Історія транзакцій за категорією</p>
            </div>
          </div>
          
          <div class="w-full md:w-64">
            <select 
              v-model="selectedTrendCategoryId"
              class="w-full px-4 py-3 rounded-2xl bg-gray-50 border-2 border-gray-100 font-bold text-gray-700 focus:border-fuchsia-500 focus:ring-4 focus:ring-fuchsia-100 transition-all outline-none"
            >
              <optgroup label="Всі категорії">
                <option v-for="cat in store.categories.all" :key="cat.id" :value="cat.id">
                  {{ cat.name }}
                </option>
              </optgroup>
            </select>
          </div>
        </div>
        
        <div class="flex-grow relative min-h-[400px]">
          <Line 
            v-if="categoryTrendData && categoryTrendData.datasets[0].data.some(v => v > 0)"
            :data="categoryTrendData" 
            :options="categoryAreaOptions" 
          />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 gap-4">
            <CalendarDays :size="48" stroke-width="1.5" class="opacity-50" />
            <span class="font-black tracking-widest uppercase text-sm">Оберіть категорію з транзакціями</span>
          </div>
        </div>
      </div>
    </div>

      <ExportCsvPanel
        class="mt-8"
        :start-date="store.filters.startDate"
        :end-date="store.filters.endDate"
        :year="exportYear"
      />
    </div> <!-- Закінчення activeTab === 'overview' -->

    <!-- Вкладка Транзакції -->
    <div v-if="activeTab === 'transactions'" class="animate-fade-in space-y-6">
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h2 class="text-2xl font-black text-gray-800 tracking-tight">Історія транзакцій</h2>
        <button 
          @click="openCreateModal"
          class="w-full md:w-auto bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-2xl font-black shadow-lg shadow-blue-200 hover:scale-[1.02] transition-all flex items-center justify-center gap-2"
        >
          <Plus :size="20" stroke-width="3" />
          Додати запис
        </button>
      </div>

      <TransactionList 
        :transactions="store.transactions"
        :isLoading="store.isLoading"
        :getCategoryName="store.getCategoryName"
        @open-details="openTransactionDetails"
      />
    </div>

    <!-- Вкладка Бюджети -->
    <div v-if="activeTab === 'budgets'" class="animate-fade-in">
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <h2 class="text-2xl font-black text-gray-800 tracking-tight">Ліміти витрат</h2>
        <button @click="openBudgetForm()" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-2xl transition-all shadow-lg shadow-blue-200">+ Новий Бюджет</button>
      </div>
      
      <div v-if="budgetStore.isLoading" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SkeletonLoader height="150px" borderRadius="1.5rem" />
        <SkeletonLoader height="150px" borderRadius="1.5rem" />
      </div>
      <div v-else-if="budgetStore.budgetProgress.length === 0" class="bg-white p-12 rounded-[2.5rem] border border-gray-100 text-center shadow-xl shadow-gray-200/40">
        <div class="w-16 h-16 bg-blue-50 text-blue-500 rounded-full mx-auto flex items-center justify-center mb-4"><PieChart size="32" stroke-width="2.5" /></div>
        <h3 class="text-xl font-bold text-gray-800 mb-2">Немає активних бюджетів</h3>
        <p class="text-gray-500">Створіть свій перший ліміт, щоб контролювати витрати.</p>
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <BudgetCard 
          v-for="budget in budgetStore.budgetProgress" 
          :key="budget.id" 
          :budget="budget" 
          :categoryName="budget.category_id ? store.getCategoryName(budget.category_id) : 'Загальний бюджет'"
          @edit="openBudgetForm"
          @delete="deleteBudget"
        />
      </div>
    </div> <!-- Закінчення activeTab === 'budgets' -->

    <!-- Вкладка Історія податків -->
    <div v-if="activeTab === 'history'" class="animate-fade-in space-y-8">
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
        <div>
          <h2 class="text-2xl font-black text-gray-800 tracking-tight">Історія нарахувань</h2>
          <p class="text-sm font-bold text-gray-400 mt-1">Архів розрахованих податків та доходів ФОП</p>
        </div>
        <div class="flex flex-wrap gap-3">
          <button 
            @click="syncAllHistory"
            :disabled="isSyncingTax"
            class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-3 px-8 rounded-2xl transition-all shadow-lg flex items-center gap-3"
          >
            <Loader2 v-if="isSyncingTax" class="animate-spin" :size="20" />
            <TrendingUp v-else :size="20" stroke-width="3" />
            Синхронізувати всю історію
          </button>
        </div>
      </div>

      <div class="bg-white rounded-[2.5rem] border border-gray-100 shadow-xl shadow-gray-200/40 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-gray-50/50 border-b border-gray-100">
                <th class="px-8 py-5 text-xs font-black text-gray-400 uppercase tracking-widest">Період</th>
                <th class="px-8 py-5 text-xs font-black text-gray-400 uppercase tracking-widest">Дохід ФОП</th>
                <th class="px-8 py-5 text-xs font-black text-gray-400 uppercase tracking-widest">ЄСВ</th>
                <th class="px-8 py-5 text-xs font-black text-gray-400 uppercase tracking-widest">Єдиний (ЄП)</th>
                <th class="px-8 py-5 text-xs font-black text-gray-400 uppercase tracking-widest">Військовий (ВЗ)</th>
                <th class="px-8 py-5 text-xs font-black text-gray-400 uppercase tracking-widest text-right">Разом</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50">
              <tr v-for="record in budgetStore.taxHistory" :key="record.id" class="hover:bg-blue-50/30 transition-colors group">
                <td class="px-8 py-6">
                  <span class="font-black text-gray-900">{{ record.month.toString().padStart(2, '0') }}.{{ record.year }}</span>
                </td>
                <td class="px-8 py-6 font-bold text-gray-700">
                  {{ Number(record.fop_income).toLocaleString('uk-UA') }} ₴
                </td>
                <td class="px-8 py-6 font-black" :class="record.esv > 0 ? 'text-indigo-600' : 'text-gray-300'">
                  {{ Number(record.esv).toLocaleString('uk-UA') }} ₴
                </td>
                <td class="px-8 py-6 font-black" :class="record.income_tax > 0 ? 'text-blue-600' : 'text-gray-300'">
                  {{ Number(record.income_tax).toLocaleString('uk-UA') }} ₴
                </td>
                <td class="px-8 py-6 font-black" :class="record.military_tax > 0 ? 'text-fuchsia-600' : 'text-gray-300'">
                  {{ Number(record.military_tax).toLocaleString('uk-UA') }} ₴
                </td>
                <td class="px-8 py-6 font-black text-gray-900 text-right">
                  {{ Number(record.esv + record.income_tax + record.military_tax).toLocaleString('uk-UA') }} ₴
                </td>
              </tr>
              <tr v-if="budgetStore.taxHistory.length === 0">
                <td colspan="6" class="px-8 py-20 text-center">
                  <div class="flex flex-col items-center gap-4 text-gray-300">
                    <CalendarDays :size="48" stroke-width="1.5" />
                    <p class="font-black uppercase tracking-widest text-sm">Історія поки що порожня</p>
                    <p class="text-xs text-gray-400 max-w-xs mx-auto">Натисніть "Оновити поточний місяць", щоб зафіксувати дані для поточного періоду.</p>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Група ФОП -->
    <div v-if="activeTab === 'fop_group'" class="animate-fade-in">
      <FopGroupRecommendPanel
        :start-date="store.filters.startDate"
        :end-date="store.filters.endDate"
      />
    </div>

    <!-- Вкладка Звіти та поведінка -->
    <div v-if="activeTab === 'reports'" class="animate-fade-in flex flex-col gap-8">
      <div class="flex justify-between items-center mb-6">
         <h2 class="text-2xl font-black text-gray-800 tracking-tight">Розширена Аналітика</h2>
      </div>

      <div v-if="budgetStore.insights?.summary" class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="bg-white p-6 rounded-[2rem] border border-blue-100 shadow-xl shadow-blue-100/20">
          <p class="text-sm font-bold text-blue-500 uppercase tracking-wider mb-2">Залишок після витрат</p>
          <span class="text-3xl font-black text-gray-900">{{ budgetStore.insights.summary.savings_rate }}%</span>
        </div>
        <div class="bg-white p-6 rounded-[2rem] border border-indigo-100 shadow-xl shadow-indigo-100/20">
          <p class="text-sm font-bold text-indigo-500 uppercase tracking-wider mb-2">Три головні категорії</p>
          <span class="text-3xl font-black text-gray-900">{{ budgetStore.insights.summary.top3_concentration }}%</span>
        </div>
        <div class="bg-white p-6 rounded-[2rem] border border-gray-100 shadow-xl shadow-gray-200/20 md:col-span-2">
          <p class="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">Період аналізу</p>
          <span class="text-lg font-black text-gray-900">
            з {{ budgetStore.insights.summary.start_date }} по {{ budgetStore.insights.summary.end_date }}
          </span>
          <p class="text-xs text-gray-400 mt-2">
            Порівнюємо з попереднім періодом: з {{ budgetStore.insights.summary.previous_start_date }} по {{ budgetStore.insights.summary.previous_end_date }}
          </p>
        </div>
      </div>

      <div v-if="budgetStore.insights?.global_recommendations?.length" class="bg-white p-6 sm:p-8 rounded-[2.5rem] shadow-xl shadow-green-100/20 border border-green-50 flex flex-col gap-4">
        <h3 class="text-xl font-black text-gray-800 flex items-center gap-3">
          <span class="w-10 h-10 bg-green-100 flex items-center justify-center rounded-xl text-green-600">
            <TrendingUp size="20" stroke-width="2.5"/>
          </span>
          Загальні поради
        </h3>
        <div
          v-for="(tip, idx) in budgetStore.insights.global_recommendations"
          :key="`global-${idx}`"
          class="p-4 bg-green-50 text-green-900 rounded-2xl font-medium border border-green-100"
        >
          {{ tip }}
        </div>
      </div>

      <div v-if="budgetStore.insights?.category_insights?.length" class="bg-white p-6 sm:p-8 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col gap-4">
        <h3 class="text-xl font-black text-gray-800">Інсайти по категоріях витрат</h3>
        <div
          v-for="item in budgetStore.insights.category_insights"
          :key="item.category_id"
          class="rounded-2xl border border-gray-100 p-5 bg-gray-50/50"
        >
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <p class="text-lg font-black text-gray-900">{{ item.category_name }}</p>
              <p class="text-sm text-gray-500">
                Зараз: {{ Number(item.spent_current).toLocaleString('uk-UA') }} ₴,
                минулий період: {{ Number(item.spent_previous).toLocaleString('uk-UA') }} ₴
              </p>
            </div>
            <div class="flex items-center gap-3">
              <span class="px-3 py-1 rounded-full text-xs font-black uppercase border" :class="severityBadgeClass(item.severity)">
                {{ severityLabel(item.severity) }} ризик
              </span>
              <span class="text-sm font-black text-gray-700">Оцінка: {{ item.risk_score }}</span>
            </div>
          </div>

          <p class="mt-3 text-sm text-gray-700 leading-relaxed">{{ item.conclusion }}</p>

          <div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-bold text-gray-600">
            <span>Частка у витратах: {{ item.share_of_total }}%</span>
            <span>Зміна до минулого періоду: {{ item.delta_pct > 0 ? '+' : '' }}{{ item.delta_pct }}%</span>
            <span v-if="item.budget_usage_pct !== null">Використання бюджету: {{ item.budget_usage_pct }}%</span>
          </div>

          <ul class="mt-3 space-y-2">
            <li
              v-for="(rec, idx) in item.recommendations"
              :key="`${item.category_id}-${idx}`"
              class="text-sm text-blue-900 bg-blue-50 border border-blue-100 rounded-xl px-3 py-2"
            >
              {{ rec }}
            </li>
          </ul>

          <div class="mt-4">
            <button
              @click="openCategoryTransactions(item.category_id)"
              class="text-xs font-black uppercase tracking-widest text-blue-600 hover:text-blue-800"
            >
              Переглянути транзакції категорії →
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <BudgetForm v-if="isBudgetFormOpen" :budgetToEdit="budgetToEdit" @close="closeBudgetForm" />

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
      @saved="submitNewCategory"
    />

    <TransactionModal 
      :isOpen="isDetailModalOpen"
      :transaction="selectedTransaction"
      :userId="userId"
      :fopSettings="fopSettings"
      @close="isDetailModalOpen = false; selectedTransaction = null"
      @updated="handleTransactionUpdate"
      @deleted="handleTransactionUpdate"
    />
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
