<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
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
import { PieChart, ArrowUpRight, ArrowDownLeft, TrendingUp, BarChart3, CalendarDays } from 'lucide-vue-next';
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';
import TransactionFilters from '@/components/transactions/TransactionFilters.vue';

ChartJS.register(
  Title, Tooltip, Legend, ArcElement, CategoryScale, 
  LinearScale, PointElement, LineElement, BarElement, Filler
);

const store = useTransactionStore();
const router = useRouter();

onMounted(async () => {
  // Fetch everything needed for analytics
  await Promise.all([
    store.fetchTransactions(),
    store.fetchCategories()
  ]);
});

watch(() => store.filters, () => {
  store.fetchTransactions();
}, { deep: true });

const resetFilters = () => {
  store.filters = { startDate: '', endDate: '', type: '', categoryId: '' };
};

// Helper to accumulate amounts by category
const getChartData = (type) => {
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
  const dates = [...new Set(store.transactions.map(t => t.transaction_date))];
  return dates.sort((a, b) => new Date(a) - new Date(b));
});

// Helper to group transactions by date and type
const getGroupedByDate = (type, categoryId = null) => {
  const grouped = {};
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
        <p class="text-gray-500 font-medium mt-2 text-lg">Огляд витрат та доходів за категоріями</p>
      </div>
    </header>

    <!-- Filters Bar Sync with Transactions -->
    <TransactionFilters 
      v-model:filters="store.filters"
      @reset="resetFilters"
    />

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
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
